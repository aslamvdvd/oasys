"""
Management command to parse standard Syslog files (e.g., /var/log/syslog) 
and send entries to the log_service.

Inherits state management from BaseLogParserCommand.
Parses a common syslog format.

Example Usage:
    python manage.py parse_syslog --log-file /var/log/syslog
    python manage.py parse_syslog --log-file /path/to/custom_sys.log --state-dir /opt/parser_states
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

# --- Regex Definition --- 
SYSLOG_RE = re.compile(
    r'^(?P<month>\w{3})\s+(?P<day>\s?\d{1,2}) (?P<time>\d{2}:\d{2}:\d{2}) (?P<hostname>\S+) (?P<process>[a-zA-Z0-9\/\._-]+)(?:\[(?P<pid>\d+)\])?: (?P<message>.*)$'
)

class Command(BaseLogParserCommand): # Inherit from Base
    help = 'Parses Syslog files and sends events to log_service.'
    parser_name = "syslog" # Define parser name

    # Inherits add_arguments from BaseLogParserCommand

    def handle(self, *args, **options):
        if not HAS_LOG_SERVICE:
            raise CommandError("Log service (LOGS_DIR setting) is not configured. Cannot run parser.")
            
        log_parser_re = SYSLOG_RE
             
        # Setup paths using base class method
        self._setup_paths_and_logger(options)
        log_file_name = self.log_file_path.name

        try:
            # Load state using base class method
            self._load_state()
            processed_lines = 0
            parse_errors = 0
            current_year = datetime.now().year 
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
                            # Pass current_year to processing function
                            self._process_log_entry(parsed_data, log_file_name, line, current_year)
                            processed_lines += 1
                        else:
                            logger.warning(f"Line did not match syslog format: {line[:200]}...")
                            parse_errors += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing line: {line[:200]}... Error: {e}", exc_info=True)
                        parse_errors += 1
                        
                    self.last_offset = log_file.tell()

            # Save state using base class method
            self._save_state()

            self.stdout.write(self.style.SUCCESS(
                f"Finished parsing syslog. Processed: {processed_lines} lines. Parse errors: {parse_errors}. "
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
    def _process_log_entry(self, data: dict, log_file_name: str, original_line: str, current_year: int):
        """Processes a parsed syslog line dictionary and logs it."""
        try:
            dt_str = f"{data['month']} {data['day']} {current_year} {data['time']}"
            original_timestamp_str = f"{data['month']} {data['day']} {data['time']}"
            timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
            try:
                local_dt = datetime.strptime(dt_str, '%b %d %Y %H:%M:%S')
                aware_local_dt = local_dt.astimezone()
                utc_dt = aware_local_dt.astimezone(timezone.utc)
                if utc_dt > datetime.now(timezone.utc) + timedelta(days=1):
                    logger.debug(f"Parsed date {utc_dt} is in future, assuming previous year.")
                    local_dt = datetime.strptime(f"{data['month']} {data['day']} {current_year-1} {data['time']}", '%b %d %Y %H:%M:%S')
                    aware_local_dt = local_dt.astimezone()
                    utc_dt = aware_local_dt.astimezone(timezone.utc)
                timestamp = utc_dt.isoformat(timespec='seconds').replace('+00:00', 'Z')
            except ValueError as e:
                logger.warning(f"Could not parse syslog timestamp '{dt_str}': {e}. Using current time.")

            message = data.get('message', '').strip()
            severity = LogSeverity.INFO 
            
            extra = {
                'original_line': original_line,
                'original_timestamp': original_timestamp_str,
                'hostname': data.get('hostname'),
                'process': data.get('process'),
                'pid': data.get('pid'),
            }
            
            log_event(
                event_type=LogEventType.SYSTEM_SYSLOG,
                event_name='syslog_entry',
                severity=severity,
                source=f'parser.syslog.{log_file_name}',
                message=message,
                timestamp=timestamp,
                extra_data={k: v for k, v in extra.items() if v is not None}
            )
            
        except Exception as e:
            logger.error(f"Unexpected error formatting log entry: {e}. Data: {data}", exc_info=True)

    # (Optional unmatched line logger removed for brevity)