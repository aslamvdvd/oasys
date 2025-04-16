"""
Management command to parse UFW (Uncomplicated Firewall) logs 
(e.g., /var/log/ufw.log or from syslog) and send entries to the log_service.

Inherits state management from BaseLogParserCommand.
Parses the common UFW log format prefixed by syslog-like headers.

Example Usage:
    python manage.py parse_ufw --log-file /var/log/ufw.log
    python manage.py parse_ufw --log-file /var/log/syslog --state-dir /opt/parser_states 
"""

import os
import re
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from django.core.management.base import CommandError 
from django.conf import settings

from ..base_parser import BaseLogParserCommand
from log_service.events import LogEventType, LogSeverity
from log_service.logger import log_event
from log_service.utils import HAS_LOG_SERVICE

logger = logging.getLogger(__name__)

# --- Regex Definitions ---

# 1. Match the modern timestamp prefix 
# Example: 2025-04-16T07:48:27.158323+05:30 PrinceOfLands kernel: [ ...
SYSLOG_PREFIX_RE = re.compile(
    # Capture the timestamp string robustly
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+[+-]\d{2}:\d{2})\s+'
    r'(?P<hostname>\S+)\s+' 
    r'(?P<process>kernel):\s+\[\s*(?P<kernel_timestamp>\d+\.\d+)\s*\]\s+'
    r'(?P<message>.*)$' 
)

# 2. Parse the message part for UFW details
#    Handles optional fields like interfaces, MAC, packet details.
UFW_DETAIL_RE = re.compile(
    r'\[UFW\s+(?P<action>\w+)\]\s+'  # Action (BLOCK, ALLOW, etc.)
    r'(?:IN=(?P<in_interface>\S*)\s*)?'
    r'(?:OUT=(?P<out_interface>\S*)\s*)?'
    r'(?:MAC=(?P<mac_address>[0-9a-fA-F:]+)\s*)?'
    r'SRC=(?P<src_ip>\S+)\s+' # Keep the mandatory src_ip
    r'DST=(?P<dst_ip>\S+)\s+'
    r'(?:LEN=(?P<len>\d+)\s*)?'
    r'(?:TOS=(?P<tos>0x[0-9a-fA-F]+)\s*)?'
    r'(?:PREC=(?P<prec>0x[0-9a-fA-F]+)\s*)?'
    r'(?:TTL=(?P<ttl>\d+)\s*)?'
    r'(?:ID=(?P<id>\S+)\s*)?'
    r'(?:DF\s*)?'  # Don't Fragment flag
    r'(?:WINDOW=(?P<window>\d+)\s*)?'
    r'(?:RES=(?P<res>0x[0-9a-fA-F]+)\s*)?'
    r'(?:(SYN|ACK|FIN|RST|URG|PSH)(?:\s+|$))?' # Common TCP flags (might need more detail)
    r'PROTO=(?P<protocol>\S+)' 
    r'(?:\s+SPT=(?P<src_port>\d+))?'
    r'(?:\s+DPT=(?P<dst_port>\d+))?'
    r'.*' # Catch any remaining details
)

# Map UFW actions to severity
UFW_SEVERITY_MAP = {
    'BLOCK': LogSeverity.WARNING,
    'ALLOW': LogSeverity.INFO,
    'AUDIT': LogSeverity.INFO,
    'DENY': LogSeverity.WARNING, # Similar to BLOCK
}

class Command(BaseLogParserCommand): # Inherit from Base
    help = 'Parses UFW firewall logs and sends events to log_service.'
    parser_name = "ufw" # Define parser name

    # Inherits add_arguments from BaseLogParserCommand

    def handle(self, *args, **options):
        if not HAS_LOG_SERVICE:
            raise CommandError("Log service (LOGS_DIR setting) is not configured. Cannot run parser.")
            
        # Setup paths using base class method
        self._setup_paths_and_logger(options)
        log_file_name = self.log_file_path.name

        try:
            # Load state using base class method
            self._load_state()
            processed_lines = 0
            parse_errors = 0
            event_logged_count = 0
            current_year = datetime.now().year
            # self.last_offset initialized by _load_state

            with open(self.log_file_path, 'r', encoding='utf-8', errors='replace') as log_file:
                log_file.seek(self.start_offset)
                
                while True: # Loop using readline
                    line = log_file.readline()
                    if not line:
                        self.last_offset = log_file.tell() # Capture final position
                        break
                        
                    line = line.strip()
                    if not line or '[UFW ' not in line: # Quick pre-filter
                        self.last_offset = log_file.tell() 
                        continue
                        
                    processed_lines += 1
                    
                    try:
                        syslog_match = SYSLOG_PREFIX_RE.match(line)
                        if syslog_match:
                            syslog_data = syslog_match.groupdict()
                            ufw_message = syslog_data.get('message', '')
                            
                            ufw_match = UFW_DETAIL_RE.search(ufw_message) # Use search as details might be embedded
                            if ufw_match:
                                ufw_data = ufw_match.groupdict()
                                logged = self._process_log_entry(
                                    syslog_data, ufw_data, log_file_name, line, current_year
                                )
                                if logged:
                                     event_logged_count += 1
                            else:
                                # Matched syslog prefix but not UFW details - likely different kernel message
                                logger.debug(f"Line matched syslog prefix but not UFW details: {line[:200]}...")
                                parse_errors += 1
                        else:
                            # Did not match syslog prefix, might be a differently formatted line
                            logger.warning(f"Line did not match expected syslog prefix format: {line[:200]}...")
                            parse_errors += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing line: {line[:200]}... Error: {e}", exc_info=True)
                        parse_errors += 1
                        
                    self.last_offset = log_file.tell()

            # Save state using base class method
            self._save_state()

            self.stdout.write(self.style.SUCCESS(
                f"Finished parsing UFW log. Lines checked: {processed_lines}. Events logged: {event_logged_count}. Parse errors: {parse_errors}. "
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
    def _process_log_entry(self, syslog_data: dict, ufw_data: dict, log_file_name: str, original_line: str, current_year: int) -> bool:
        """Processes a parsed UFW log line dictionary and logs it. Returns True if logged."""
        try:
            # --- Timestamp Processing (Using the captured ISO-like timestamp) ---
            original_timestamp_str = syslog_data.get('timestamp')
            log_timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z') # Fallback
            if original_timestamp_str:
                try:
                    # Parse the timestamp string (may include timezone)
                    # datetime.fromisoformat handles many ISO 8601 formats
                    parsed_dt = datetime.fromisoformat(original_timestamp_str)
                    # Ensure it's timezone-aware and convert to UTC
                    if parsed_dt.tzinfo is None:
                        # If no timezone info, assume local (less ideal)
                        aware_local_dt = parsed_dt.astimezone()
                        utc_dt = aware_local_dt.astimezone(timezone.utc)
                    else:
                        # Already timezone-aware, just convert to UTC
                        utc_dt = parsed_dt.astimezone(timezone.utc)
                        
                    log_timestamp = utc_dt.isoformat(timespec='seconds').replace('+00:00', 'Z')
                except ValueError as e:
                    logger.warning(f"Could not parse UFW timestamp '{original_timestamp_str}': {e}. Using current time.")
            else:
                logger.warning(f"No timestamp found in syslog_data. Using current time.")

            # --- Event Details ---
            action = ufw_data.get('action', 'UNKNOWN').upper()
            event_name = f"ufw_{action.lower()}"
            severity = UFW_SEVERITY_MAP.get(action, LogSeverity.INFO)
            
            src_ip = ufw_data.get('src_ip')
            dst_ip = ufw_data.get('dst_ip')
            protocol = ufw_data.get('protocol')
            src_port = ufw_data.get('src_port')
            dst_port = ufw_data.get('dst_port')
            
            # --- Prepare Extra Data ---
            extra = {
                'original_line': original_line,
                'original_timestamp': original_timestamp_str, # Use the full timestamp string
                'hostname': syslog_data.get('hostname'),
                'kernel_timestamp': syslog_data.get('kernel_timestamp'),
                'firewall_action': action,
                'src_ip': src_ip,
                'dst_ip': dst_ip,
                'protocol': protocol,
                'src_port': int(src_port) if src_port else None,
                'dst_port': int(dst_port) if dst_port else None,
                'in_interface': ufw_data.get('in_interface'),
                'out_interface': ufw_data.get('out_interface'),
                'mac_address': ufw_data.get('mac_address'),
                'packet_len': int(ufw_data['len']) if ufw_data.get('len') else None,
                'packet_ttl': int(ufw_data['ttl']) if ufw_data.get('ttl') else None,
                'packet_id': ufw_data.get('id'),
                'packet_tos': ufw_data.get('tos'),
                'packet_prec': ufw_data.get('prec'),
                'tcp_window': int(ufw_data['window']) if ufw_data.get('window') else None,
                'tcp_res': ufw_data.get('res'),
                # Add more parsed fields if needed (TCP flags etc.)
            }

            # --- Log Event ---
            log_event(
                event_type=LogEventType.FIREWALL,
                event_name=event_name,
                severity=severity,
                source=f'parser.ufw.{log_file_name}',
                message=f"UFW {action}: SRC={src_ip or '?'} DST={dst_ip or '?'} PROTO={protocol or '?'}", # Concise message
                # ip_address=src_ip, # Use src_ip in extra_data
                # timestamp=log_timestamp, # Use log_event's timestamp
                extra_data={k: v for k, v in extra.items() if v is not None}
            )
            return True # Logged successfully
            
        except Exception as e:
            logger.error(f"Unexpected error formatting UFW log entry: {e}. Data: {ufw_data}", exc_info=True)
            return False # Did not log 