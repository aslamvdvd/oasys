"""
Management command to parse Nginx ERROR logs and send entries to the log_service.

Inherits state management from BaseLogParserCommand.
Parses the standard Nginx error log format.

Example Usage:
    python manage.py parse_nginx_error --log-file /var/log/nginx/error.log
    python manage.py parse_nginx_error --log-file /path/to/custom_error.log --state-dir /opt/parser_states
"""

import os
import re
import json # Not used directly
import hashlib # Not used directly
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
# Removed BaseCommand, CommandError
from django.core.management.base import CommandError
from django.conf import settings
# Import Base class
from ..base_parser import BaseLogParserCommand
from log_service.events import LogEventType, LogSeverity
from log_service.logger import log_event
from log_service.utils import HAS_LOG_SERVICE

logger = logging.getLogger(__name__)

# --- Regex and Mapping --- 
NGINX_ERROR_RE = re.compile(
    r'^(?P<datetime>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) \[(?P<level>\w+)\] (?P<pid>\d+)#(?P<tid>\d+): (?:\*(?P<cid>\d+) )?(?P<message>.*?)(?:, client: (?P<client>[^,]+))?(?:, server: (?P<server>[^,]+))?(?:, request: "(?P<request>[^"]*)")?(?:, upstream: "(?P<upstream>[^"]*)")?(?:, host: "(?P<host>[^"]*)")?$'
)
NGINX_LEVEL_MAP = {
    'debug': LogSeverity.DEBUG,
    'info': LogSeverity.INFO,
    'notice': LogSeverity.INFO,
    'warn': LogSeverity.WARNING,
    'error': LogSeverity.ERROR,
    'crit': LogSeverity.CRITICAL,
    'alert': LogSeverity.CRITICAL,
    'emerg': LogSeverity.CRITICAL,
}

class Command(BaseLogParserCommand): # Inherit from Base
    help = 'Parses Nginx ERROR logs and sends events to log_service.'
    parser_name = "nginx_error" # Define parser name

    # Inherits add_arguments from BaseLogParserCommand (for --log-file, --state-dir)

    def handle(self, *args, **options):
        if not HAS_LOG_SERVICE:
            raise CommandError("Log service (LOGS_DIR setting) is not configured. Cannot run parser.")
            
        log_parser_re = NGINX_ERROR_RE 
             
        # Setup paths using base class method
        self._setup_paths_and_logger(options)
        log_file_name = self.log_file_path.name

        try:
            # Load state using base class method
            self._load_state()
            processed_lines = 0
            parse_errors = 0
            # self.last_offset initialized by _load_state

            with open(self.log_file_path, 'r', encoding='utf-8', errors='replace') as log_file:
                log_file.seek(self.start_offset)
                
                while True: # Loop using readline
                    current_pos = log_file.tell()
                    line = log_file.readline()
                    if not line:
                        self.last_offset = log_file.tell() # Capture final position
                        break
                        
                    line = line.strip()
                    if not line: 
                        continue
                        
                    try:
                        match = log_parser_re.match(line)
                        if match:
                            parsed_data = match.groupdict()
                            self._process_log_entry(parsed_data, log_file_name, line)
                            processed_lines += 1
                        else:
                            logger.warning(f"Line did not match Nginx error format: {line[:200]}...")
                            parse_errors += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing line: {line[:200]}... Error: {e}", exc_info=True)
                        parse_errors += 1
                        
                    self.last_offset = log_file.tell() 

            # Save state using base class method
            self._save_state()

            self.stdout.write(self.style.SUCCESS(
                f"Finished parsing error log. Processed: {processed_lines} lines. Parse errors: {parse_errors}. "
                f"Current offset: {self.last_offset}."
            ))

        except FileNotFoundError:
            raise CommandError(f"Log file disappeared during parsing: {self.log_file_path}")
        except PermissionError:
            raise CommandError(f"Permission denied reading log file or writing state file.")
        except Exception as e:
            logger.error(f"Unhandled error during parsing: {e}", exc_info=True)
            if self.current_inode is not None and self.last_offset is not None:
                try:
                    self._save_state()
                except Exception as save_e:
                     logger.error(f"Failed to save state during error handling: {save_e}")
            raise CommandError(f"An unexpected error occurred: {e}")
            
    # Removed _load_state and _save_state - inherited
            
    # --- Log Entry Processing --- 
    def _process_log_entry(self, data: dict, log_file_name: str, original_line: str):
        """Processes a parsed error log line dictionary and logs it."""
        try:
            # Extract key fields for log_event
            message = data.get('message', original_line)
            severity = NGINX_LEVEL_MAP.get(data.get('level'), LogSeverity.ERROR)
            ip_address = data.get('client') # Use client IP if available
            timestamp = self._parse_timestamp(data.get('datetime'))

            extra = {
                'original_line': original_line,
                'original_timestamp': data.get('datetime'),
                'nginx_log_level': data.get('level'),
                'nginx_pid': data.get('pid'),
                'nginx_tid': data.get('tid'),
                'nginx_cid': data.get('cid'),
                'nginx_client': data.get('client'),
                'nginx_server': data.get('server'),
                'nginx_request': data.get('request'),
                'nginx_upstream': data.get('upstream'),
                'nginx_host': data.get('host'),
                 # Standardize on src_ip in extra_data
                'src_ip': ip_address 
            }

            log_event(
                event_type=LogEventType.SERVER_ERROR,
                event_name='nginx_error', 
                severity=severity,
                source=f'parser.nginx_error.{log_file_name}',
                message=message,
                extra_data={k: v for k, v in extra.items() if v is not None}
            )
            
        except Exception as e:
            logger.error(f"Unexpected error formatting log entry: {e}. Data: {data}", exc_info=True)

    # def _log_unmatched_line(self, line: str, log_file_name: str):
    #     """Logs lines that didn't match the expected format."""
    #     log_event(
    #         event_type=LogEventType.SERVER_ERROR,
    #         event_name='unmatched_error_log_line',
    #         severity=LogSeverity.WARNING,
    #         source=f'parser.nginx.error.{log_file_name}',
    #         message='Line did not match expected Nginx error format',
    #         extra_data={'original_line': line}
    #     ) 