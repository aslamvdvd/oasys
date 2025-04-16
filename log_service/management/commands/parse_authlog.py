"""
Management command to parse standard Linux Authentication logs (e.g., /var/log/auth.log)
and send entries to the log_service.

Inherits state management from BaseLogParserCommand.
Parses a common syslog-like format and interprets the message content for auth events.

Example Usage:
    python manage.py parse_authlog --log-file /var/log/auth.log
    python manage.py parse_authlog --log-file /path/to/secure.log --state-dir /opt/parser_states
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
from log_service.events import (
    LogEventType, 
    LogSeverity,
    EVENT_AUTH_SUCCESS, EVENT_AUTH_FAILURE, EVENT_AUTH_SESSION_OPEN, EVENT_AUTH_SESSION_CLOSE
)
from log_service.logger import log_event
from log_service.utils import HAS_LOG_SERVICE

logger = logging.getLogger(__name__)

# --- Regex Definitions --- 
SYSLOG_RE = re.compile(
    r'^(?P<month>\w{3})\s+(?P<day>\s?\d{1,2}) (?P<time>\d{2}:\d{2}:\d{2}) (?P<hostname>\S+) (?P<process>[a-zA-Z0-9\/\._-]+)(?:\[(?P<pid>\d+)\])?: (?P<message>.*)$'
)
RE_SESSION_OPEN = re.compile(r'session opened for user (?P<user>\S+)(?: by \(uid=(?P<uid>\d+)\))?')
RE_SESSION_CLOSE = re.compile(r'session closed for user (?P<user>\S+)')
RE_ACCEPTED_PWD = re.compile(r'Accepted password for (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)')
RE_AUTH_FAILURE = re.compile(r'authentication failure;.* user=(?P<user>\S*).*(?: rhost=(?P<ip>\S+))?')
RE_FAILED_PWD = re.compile(r'Failed password for(?: invalid user)? (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)')
RE_INVALID_USER = re.compile(r'Invalid user (?P<user>\S+) from (?P<ip>\S+)')
RE_SUDO = re.compile(r'sudo: *(?P<user>\S+) *: *TTY=(?P<tty>\S+) *; *PWD=(?P<pwd>\S+) *; *USER=(?P<runas>\S+) *; *COMMAND=(?P<cmd>.*)')

class Command(BaseLogParserCommand): # Inherit from Base
    help = 'Parses Linux authentication logs (auth.log/secure) and sends events to log_service.'
    parser_name = "authlog" # Define parser name

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
                            self._process_log_entry(parsed_data, log_file_name, line, current_year)
                            processed_lines += 1
                        else:
                            logger.warning(f"Line did not match base auth log format: {line[:200]}...")
                            parse_errors += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing line: {line[:200]}... Error: {e}", exc_info=True)
                        parse_errors += 1
                        
                    self.last_offset = log_file.tell()

                # self.last_offset = log_file.tell() # Already set within/after loop

            # Save state using base class method
            self._save_state()

            self.stdout.write(self.style.SUCCESS(
                f"Finished parsing auth log. Processed: {processed_lines} lines checked. Parse errors: {parse_errors}. "
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
        """Processes a parsed auth log line, extracts details, and logs it."""
        try:
            hostname = data.get('hostname')
            process = data.get('process')
            pid = data.get('pid')
            message = data.get('message', '').strip()
            
            dt_str = f"{data['month']} {data['day']} {current_year} {data['time']}"
            original_timestamp_str = f"{data['month']} {data['day']} {data['time']}"
            timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
            try:
                local_dt = datetime.strptime(dt_str, '%b %d %Y %H:%M:%S')
                aware_local_dt = local_dt.astimezone()
                utc_dt = aware_local_dt.astimezone(timezone.utc)
                if utc_dt > datetime.now(timezone.utc) + timedelta(days=1):
                    local_dt = datetime.strptime(f"{data['month']} {data['day']} {current_year-1} {data['time']}", '%b %d %Y %H:%M:%S')
                    aware_local_dt = local_dt.astimezone()
                    utc_dt = aware_local_dt.astimezone(timezone.utc)
                timestamp = utc_dt.isoformat(timespec='seconds').replace('+00:00', 'Z')
            except ValueError as e:
                logger.warning(f"Could not parse auth timestamp '{dt_str}': {e}. Using current time.")
            
            event_name = None
            severity = LogSeverity.INFO
            details = {}
            ip_address = None
            
            m_session_open = RE_SESSION_OPEN.search(message)
            m_session_close = RE_SESSION_CLOSE.search(message)
            m_accepted_pwd = RE_ACCEPTED_PWD.search(message)
            m_failed_pwd = RE_FAILED_PWD.search(message)
            m_invalid_user = RE_INVALID_USER.search(message)
            m_auth_failure = RE_AUTH_FAILURE.search(message)
            m_sudo = RE_SUDO.search(message)
            
            if m_session_open:
                event_name = EVENT_AUTH_SESSION_OPEN
                details = m_session_open.groupdict()
            elif m_session_close:
                event_name = EVENT_AUTH_SESSION_CLOSE
                details = m_session_close.groupdict()
            elif m_accepted_pwd:
                event_name = EVENT_AUTH_SUCCESS
                details = m_accepted_pwd.groupdict()
                ip_address = details.get('ip')
                details['auth_method'] = 'password'
            elif m_failed_pwd:
                event_name = EVENT_AUTH_FAILURE
                severity = LogSeverity.WARNING
                details = m_failed_pwd.groupdict()
                ip_address = details.get('ip')
                details['reason'] = 'Failed password'
            elif m_invalid_user:
                 event_name = EVENT_AUTH_FAILURE
                 severity = LogSeverity.WARNING
                 details = m_invalid_user.groupdict()
                 ip_address = details.get('ip')
                 details['reason'] = 'Invalid user'
            elif m_auth_failure:
                event_name = EVENT_AUTH_FAILURE
                severity = LogSeverity.WARNING
                details = m_auth_failure.groupdict()
                ip_address = details.get('ip')
                details['reason'] = 'Authentication failure'
            elif m_sudo and process == 'sudo':
                 event_name = 'sudo_command'
                 severity = LogSeverity.WARNING
                 details = m_sudo.groupdict()
            
            if event_name:
                extra = {
                    'original_line': original_line,
                    'original_timestamp': original_timestamp_str,
                    'hostname': hostname,
                    'process': process,
                    'pid': pid,
                    'auth_user': details.get('user'),
                    'auth_uid': details.get('uid'),
                    'auth_method': details.get('auth_method'),
                    'auth_reason': details.get('reason'),
                    'auth_tty': details.get('tty'),
                    'auth_pwd': details.get('pwd'),
                    'auth_runas_user': details.get('runas'),
                    'auth_command': details.get('cmd'),
                    'src_ip': ip_address,
                    'src_port': details.get('port')
                }
                
                log_event(
                    event_type=LogEventType.SYSTEM_AUTH,
                    event_name=event_name,
                    severity=severity,
                    source=f'parser.auth.{log_file_name}',
                    ip_address=ip_address,
                    message=message,
                    timestamp=timestamp, 
                    extra_data={k: v for k, v in extra.items() if v is not None}
                )
            else:
                logger.debug(f"Skipping non-targeted auth log message: {message[:100]}...")
                pass 
                
        except Exception as e:
            logger.error(f"Unexpected error formatting log entry: {e}. Data: {data}", exc_info=True) 