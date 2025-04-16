"""
Management command to parse Nginx access logs and send entries to the log_service.

Inherits state management from BaseLogParserCommand.
Parses logs based on specified formats (currently supports 'combined').

Example Usage:
    python manage.py parse_nginx_access --log-file /var/log/nginx/access.log
    python manage.py parse_nginx_access --log-file /path/to/custom.log --format-name combined --state-dir /opt/parser_states
"""

import os
import re
import json # Not used directly here anymore
import hashlib # Not used directly here anymore
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
# Removed BaseCommand, CommandError - Inherited from base
from django.core.management.base import CommandError 
from django.conf import settings
# Import Base class
from ..base_parser import BaseLogParserCommand 
from log_service.events import LogEventType, LogSeverity
from log_service.logger import log_event
from log_service.utils import HAS_LOG_SERVICE

logger = logging.getLogger(__name__)

# --- Regex Definitions --- 
COMBINED_LOG_RE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<datetime>\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}) (?P<tz>[+-]\d{4})\] "(?P<method>\S+) (?P<path>\S+) (?P<protocol>HTTP/\d\.\d)" (?P<status>\d{3}) (?P<bytes>\d+) "(?P<referer>[^"]*)" "(?P<user_agent>[^"]*)".*$'
)
LOG_FORMATS = {
    'combined': COMBINED_LOG_RE,
}

class Command(BaseLogParserCommand): # Inherit from BaseLogParserCommand
    help = 'Parses Nginx access logs and sends events to log_service.'
    parser_name = "nginx_access" # Define parser name for state file

    def add_arguments(self, parser):
        # Call super to get standard --log-file, --state-dir args
        super().add_arguments(parser)
        # Add parser-specific arguments
        parser.add_argument(
            '--format-name',
            type=str,
            default='combined',
            choices=LOG_FORMATS.keys(),
            help='The named log format used in the file (default: combined).'
        )

    def handle(self, *args, **options):
        if not HAS_LOG_SERVICE:
            raise CommandError("Log service (LOGS_DIR setting) is not configured. Cannot run parser.")
            
        format_name = options['format_name']
        log_parser_re = LOG_FORMATS.get(format_name)
        if not log_parser_re:
             raise CommandError(f"Unknown log format name: {format_name}")
             
        # Setup paths and logger using the base class method
        self._setup_paths_and_logger(options)
        log_file_name = self.log_file_path.name # Get log file name after setup

        try:
            # Load state using base class method
            self._load_state()
            processed_lines = 0
            parse_errors = 0
            # self.last_offset initialized by _load_state

            with open(self.log_file_path, 'r', encoding='utf-8', errors='replace') as log_file:
                log_file.seek(self.start_offset)
                
                while True: # Loop using readline
                    current_pos = log_file.tell() # Get position before reading
                    line = log_file.readline()
                    if not line: # End of file
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
                            logger.warning(f"Line did not match Nginx access format: {line[:200]}...")
                            parse_errors += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing line: {line[:200]}... Error: {e}", exc_info=True)
                        parse_errors += 1
                        
                    # Update last_offset only after successfully processing or attempting to process
                    # Using the position *before* the readline call that produced the current line.
                    # This ensures if the script crashes mid-line, we re-read it next time.
                    # However, for simplicity and consistency with EOF, we can use the position *after* readline.
                    self.last_offset = log_file.tell() 
                    # Alternative: self.last_offset = current_pos # This is slightly safer but might misbehave with buffered reads

            # Save state using base class method
            self._save_state()

            self.stdout.write(self.style.SUCCESS(
                f"Finished parsing. Processed: {processed_lines} lines. Parse errors: {parse_errors}. "
                f"Current offset: {self.last_offset}."
            ))

        except FileNotFoundError:
            raise CommandError(f"Log file disappeared during parsing: {self.log_file_path}")
        except PermissionError:
            raise CommandError(f"Permission denied reading log file or writing state file.")
        except Exception as e:
            logger.error(f"Unhandled error during parsing: {e}", exc_info=True)
            # Try to save state even on error
            if self.current_inode is not None and self.last_offset is not None:
                try:
                    self._save_state()
                except Exception as save_e:
                     logger.error(f"Failed to save state during error handling: {save_e}")
            raise CommandError(f"An unexpected error occurred: {e}")
            
    # Removed _load_state and _save_state - inherited from base class

    def _process_log_entry(self, data: dict, log_file_name: str, original_line: str):
        """Processes a parsed log line dictionary and logs it."""
        try:
            dt_str = data['datetime']
            tz_str = data['tz']
            try:
                naive_dt = datetime.strptime(dt_str, '%d/%b/%Y:%H:%M:%S')
                tz_offset_hours = int(tz_str[1:3])
                tz_offset_minutes = int(tz_str[3:5])
                tz_delta = timedelta(hours=tz_offset_hours, minutes=tz_offset_minutes)
                if tz_str[0] == '-':
                    tz_delta = -tz_delta
                local_dt = naive_dt.replace(tzinfo=timezone(tz_delta))
                utc_dt = local_dt.astimezone(timezone.utc)
                timestamp = utc_dt.isoformat(timespec='seconds').replace('+00:00', 'Z')
            except ValueError as e:
                logger.warning(f"Could not parse timestamp '{dt_str} {tz_str}': {e}")
                timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')

            status_code = int(data['status'])
            severity = LogSeverity.WARNING if 400 <= status_code < 500 else LogSeverity.ERROR if status_code >= 500 else LogSeverity.INFO
            
            message = f"{data.get('method', '?')} {data.get('path', '?')} {status_code}"
            
            # --- Logging ---
            # Use the parsed IP address if available
            ip_address = data.get('ip')

            extra = {
                'original_line': original_line,
                'original_timestamp': f"{data.get('datetime')} {data.get('tz', '')}".strip(),
                'http_method': data.get('method'),
                'http_path': data.get('path'),
                'http_protocol': data.get('protocol'),
                'http_status': status_code,
                'http_bytes_sent': int(data.get('bytes', 0)),
                'http_referer': data.get('referer'),
                'http_user_agent': data.get('user_agent'),
                # Ensure ip_address is included here if needed elsewhere, but not passed directly
                'src_ip': ip_address # Standardize on src_ip in extra_data
            }
            
            log_event(
                event_type=LogEventType.SERVER_ACCESS,
                event_name='nginx_access', # Or derive based on status?
                severity=severity,
                source=f'parser.nginx_access.{log_file_name}',
                message=message,
                extra_data={k: v for k, v in extra.items() if v is not None}
            )
            
        except KeyError as e:
            logger.error(f"Missing expected field '{e}' in parsed data for line: {original_line[:200]}...")
        except Exception as e:
            logger.error(f"Unexpected error formatting log entry: {e}. Data: {data}", exc_info=True) 