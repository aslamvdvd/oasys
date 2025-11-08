"""
Management command to parse PostgreSQL logs (CSV or stderr format) 
and send entries to the log_service.

Handles interleaved messages (errors, statements, slow queries) from a single log file.
Slow queries are logged with LogEventType.DATABASE_SLOW_QUERY.
Errors/other statements are logged with LogEventType.DATABASE.

Assumptions for CSV format:
- Log destination is 'csvlog'.
- Default --csv-fields assumes a log_line_prefix like '%m,%u,%d,%p,%r,%a,%v,%x,%e,%s,%l,%c,%q,%h,%i,%L'
  (timestamp, user, db, pid, remote_host:port, app_name, virtual_xid, txid, sqlstate, severity, session_line, session_id, query?, remote_host, internal_query?, log_type)
- You MUST adjust --csv-fields if your log_line_prefix differs.

Stderr format parsing is basic and relies on common patterns.

Example Usage:
    # CSV (Recommended)
    python manage.py parse_postgres --log-file /var/log/postgresql/postgresql-14-main.csv 
    python manage.py parse_postgres --log-file pg.csv --csv-fields log_time,user_name,database_name,error_severity,message

    # Stderr (Less reliable)
    python manage.py parse_postgres --log-file /var/log/postgresql/postgresql-14-main.log --log-format stderr
"""

import os
import re
import csv
import logging
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import CommandError 
from django.conf import settings

from ..base_parser import BaseLogParserCommand
from log_service.events import (
    LogEventType, 
    LogSeverity, 
    EVENT_DB_ERROR, 
    EVENT_DB_SLOW_QUERY, 
    EVENT_DB_QUERY
)
from log_service.logger import log_event
from log_service.utils import HAS_LOG_SERVICE

logger = logging.getLogger(__name__)

# --- Default CSV Fields (adjust based on log_line_prefix) ---
# Common fields from a prefix like '%m,%u,%d,%p,%r,%a,%v,%x,%e,%s,%l,%c,%q,%h,%i,%L' 
# See: https://www.postgresql.org/docs/current/runtime-config-logging.html#RUNTIME-CONFIG-LOGGING-CSVLOG
DEFAULT_CSV_FIELDS = [
    'log_time','user_name','database_name','process_id','connection_from',
    'session_id','session_line_num','command_tag','session_start_time',
    'virtual_transaction_id','transaction_id','error_severity','sql_state_code',
    'message','detail','hint','internal_query','internal_query_pos','context',
    'query','query_pos','location','application_name'
]

# --- Regex for stderr format (Basic - may need refinement) ---
# Example: 2023-10-27 10:00:00.123 UTC [12345] user@db LOG: message
# Example: 2023-10-27 10:01:00.456 UTC [12346] user@db ERROR: error message
# Example: 2023-10-27 10:02:00.789 UTC [12347] user@db LOG: duration: 1234.567 ms statement: SELECT ...
STDERR_LOG_RE = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\s+\S+)\s+' # Timestamp with TZ
    r'\[(?P<pid>\d+)\]\s+' # Process ID
    r'(?:(?P<user>\S+?)@(?P<database>\S+)\s+)?' # Optional user@db
    r'(?P<severity>\w+):\s+' # Severity (LOG, ERROR, etc.)
    r'(?P<message>.*)$' # The rest is the message
)
STDERR_DURATION_RE = re.compile(r'duration:\s+(\d+\.\d+)\s+ms')
STDERR_STATEMENT_RE = re.compile(r'(?:statement|execute.*?):\s+(.*)', re.IGNORECASE | re.DOTALL)

# Map PG severity to LogSeverity
PG_SEVERITY_MAP = {
    'DEBUG': LogSeverity.DEBUG,
    'INFO': LogSeverity.INFO,
    'NOTICE': LogSeverity.INFO,
    'LOG': LogSeverity.INFO, # Default for non-errors/warnings
    'WARNING': LogSeverity.WARNING,
    'ERROR': LogSeverity.ERROR,
    'FATAL': LogSeverity.CRITICAL,
    'PANIC': LogSeverity.CRITICAL,
}

class Command(BaseLogParserCommand):
    help = 'Parses PostgreSQL logs (CSV or stderr) and sends events to log_service.'
    parser_name = "postgres"

    def add_arguments(self, parser):
        super().add_arguments(parser) # Add --log-file, --state-dir
        parser.add_argument(
            '--log-format',
            choices=['csv', 'stderr'],
            default='csv',
            help='Format of the PostgreSQL log file (csv or stderr). Default: csv'
        )
        parser.add_argument(
            '--csv-fields',
            type=str,
            default=','.join(DEFAULT_CSV_FIELDS),
            help=('Comma-separated list of field names for CSV logs, matching log_line_prefix. ' 
                  'Required if --log-format=csv.')
        )
        parser.add_argument(
            '--min-duration-ms',
            type=float,
            default=1000.0, # Default to 1 second
            help='Minimum duration (in ms) to consider a query slow (for stderr parsing). Default: 1000.0'
        )

    def handle(self, *args, **options):
        if not HAS_LOG_SERVICE:
            raise CommandError("Log service not configured.")
            
        self._setup_paths_and_logger(options)
        log_file_name = self.log_file_path.name
        log_format = options['log_format']
        csv_fields = options['csv_fields'].split(',') if options['csv_fields'] else []
        min_duration_ms = options['min_duration_ms']

        if log_format == 'csv' and not csv_fields:
             raise CommandError("--csv-fields must be provided when --log-format=csv")

        try:
            self._load_state()
            processed_lines = 0
            event_logged_count = 0
            parse_errors = 0

            with open(self.log_file_path, 'r', encoding='utf-8', errors='replace') as log_file:
                log_file.seek(self.start_offset)
                
                reader = None
                if log_format == 'csv':
                    # Skip header if starting from beginning? PG CSV logs might not have one.
                    # Assume no header for now.
                    reader = csv.reader(log_file)

                while True:
                    try:
                        if log_format == 'csv':
                            # csv.reader handles readline internally, but we need offset
                            current_pos = log_file.tell()
                            row = next(reader) # Can raise StopIteration
                            if not row:
                                self.last_offset = log_file.tell()
                                continue 
                            line_data = dict(zip(csv_fields, row))
                            original_line = ",".join(row) # Reconstruct approx line for logging
                        else: # stderr
                            current_pos = log_file.tell()
                            line = log_file.readline()
                            if not line:
                                self.last_offset = log_file.tell()
                                break # EOF
                            line = line.strip()
                            if not line:
                                self.last_offset = log_file.tell()
                                continue
                            original_line = line
                            line_data = {'raw': line} # Pass raw line for regex processing
                            
                        processed_lines += 1
                        logged = self._process_log_entry(line_data, log_format, log_file_name, original_line, min_duration_ms)
                        if logged:
                            event_logged_count += 1
                            
                        self.last_offset = log_file.tell()

                    except StopIteration: # End of file for csv.reader
                         self.last_offset = log_file.tell() 
                         break
                    except csv.Error as e:
                        logger.error(f"CSV parsing error at offset ~{current_pos}: {e}. Line: '{log_file.readline()[:200]}...'", exc_info=True)
                        parse_errors += 1
                        self.last_offset = log_file.tell() # Try to advance past bad line
                    except Exception as e:
                        logger.error(f"Error processing line at offset ~{current_pos}: {e}. Line: '{original_line[:200]}...'", exc_info=True)
                        parse_errors += 1
                        # Decide whether to advance offset on generic error - maybe not?
                        # For now, let's advance to avoid getting stuck
                        self.last_offset = log_file.tell()
            
            self._save_state()

            self.stdout.write(self.style.SUCCESS(
                f"Finished parsing PostgreSQL log ({log_format}). Lines checked: {processed_lines}. "
                f"Events logged: {event_logged_count}. Parse errors: {parse_errors}. "
                f"Current offset: {self.last_offset}."
            ))

        except FileNotFoundError:
            raise CommandError(f"Log file disappeared: {self.log_file_path}")
        except PermissionError:
            raise CommandError(f"Permission denied reading log file or writing state file.")
        except Exception as e:
            logger.error(f"Unhandled error during parsing: {e}", exc_info=True)
            if self.current_inode is not None and self.last_offset is not None:
                try: self._save_state()
                except Exception as save_e: logger.error(f"Failed to save state during error handling: {save_e}")
            raise CommandError(f"An unexpected error occurred: {e}")

    def _process_log_entry(self, data: dict, log_format: str, log_file_name: str, original_line: str, min_duration_ms: float) -> bool:
        """Processes parsed PG log data (dict from CSV or raw stderr line) and logs it."""
        try:
            event_type = LogEventType.DATABASE
            event_name = EVENT_DB_QUERY # Default assumption
            severity = LogSeverity.INFO
            query_text = None
            duration_ms = None
            message = None
            pg_severity = None
            extra = {'original_line': original_line, 'log_format': log_format}

            if log_format == 'csv':
                # --- CSV Processing --- 
                pg_severity = data.get('error_severity')
                severity = PG_SEVERITY_MAP.get(pg_severity, LogSeverity.INFO)
                message = data.get('message')
                query_text = data.get('query')
                
                # Check for slow query (duration might be in message for CSV?)
                # PG logs duration for slow queries in the 'message' field for log_min_duration_statement > 0
                # Format: "duration: 1234.567 ms statement: SELECT ..."
                # Or sometimes just "duration: 1234.567 ms" on a separate line for multi-line statements
                if message and message.startswith('duration: '):
                    duration_match = STDERR_DURATION_RE.match(message) # Reuse regex
                    if duration_match:
                        duration_ms = float(duration_match.group(1))
                        if duration_ms >= min_duration_ms:
                            event_type = LogEventType.DATABASE_SLOW_QUERY
                            event_name = EVENT_DB_SLOW_QUERY
                            # Attempt to get the actual statement from the message
                            statement_match = STDERR_STATEMENT_RE.search(message)
                            if statement_match:
                                 query_text = statement_match.group(1).strip()
                                 message = f"Slow query: {duration_ms:.3f} ms" # Override message
                            else:
                                 message = f"Slow query duration: {duration_ms:.3f} ms" # Keep original message if no statement found
                        else:
                             # Duration logged but not slow enough - treat as normal query log if query exists
                             statement_match = STDERR_STATEMENT_RE.search(message)
                             if statement_match:
                                 query_text = statement_match.group(1).strip()
                                 event_name = EVENT_DB_QUERY
                             else:
                                 # Just a duration message, maybe ignore or log as INFO?
                                 event_name = 'db_duration_info' # Generic info
                                 
                elif query_text and pg_severity == 'LOG': # Explicit statement logging
                     event_name = EVENT_DB_QUERY
                elif pg_severity in ('ERROR', 'FATAL', 'PANIC'):
                    event_name = EVENT_DB_ERROR
                elif pg_severity == 'WARNING':
                     event_name = EVENT_DB_ERROR # Treat warnings as errors for logging? Or create specific event?
                
                # Populate extra data from known CSV fields
                extra.update({k: v for k, v in data.items() if k != 'original_line' and v}) # Add all non-empty fields
            
            else: # stderr
                # --- stderr Processing --- 
                raw_line = data.get('raw', '')
                match = STDERR_LOG_RE.match(raw_line)
                if not match:
                    logger.debug(f"stderr line did not match base format: {raw_line[:200]}...")
                    return False # Cannot parse further
                
                stderr_data = match.groupdict()
                pg_severity = stderr_data.get('severity')
                severity = PG_SEVERITY_MAP.get(pg_severity, LogSeverity.INFO)
                message = stderr_data.get('message', '').strip()
                extra['timestamp_str'] = stderr_data.get('timestamp') # Keep original string
                extra['pid'] = stderr_data.get('pid')
                extra['user'] = stderr_data.get('user')
                extra['database'] = stderr_data.get('database')
                extra['pg_severity'] = pg_severity

                # Check for duration/slow query in stderr message
                duration_match = STDERR_DURATION_RE.search(message)
                if duration_match:
                    duration_ms = float(duration_match.group(1))
                    if duration_ms >= min_duration_ms:
                        event_type = LogEventType.DATABASE_SLOW_QUERY
                        event_name = EVENT_DB_SLOW_QUERY
                        statement_match = STDERR_STATEMENT_RE.search(message)
                        if statement_match:
                            query_text = statement_match.group(1).strip()
                            message = f"Slow query: {duration_ms:.3f} ms" 
                        else:
                            message = f"Slow query duration: {duration_ms:.3f} ms"
                    else:
                        # Duration logged but not slow enough
                        statement_match = STDERR_STATEMENT_RE.search(message)
                        if statement_match:
                             query_text = statement_match.group(1).strip()
                             event_name = EVENT_DB_QUERY
                        else:
                             event_name = 'db_duration_info'
                             
                elif pg_severity in ('ERROR', 'FATAL', 'PANIC', 'WARNING'):
                     event_name = EVENT_DB_ERROR
                elif query_text: # Check if we extracted a query earlier
                     event_name = EVENT_DB_QUERY
                # else: Keep default event_name (EVENT_DB_QUERY or db_duration_info)

            # --- Final Data Assembly & Logging --- 
            if duration_ms is not None:
                extra['duration_ms'] = duration_ms
            if query_text:
                extra['query_text'] = query_text 
                # Avoid duplicating query in message if already in extra_data?
                if message is None and event_name == EVENT_DB_QUERY:
                     message = f"Query: {query_text[:150]}..." # Truncate long queries for message
            
            if message is None:
                 message = original_line # Fallback message

            # Only log if we identified a specific event beyond just INFO/LOG
            # Or if it's an error/slow query
            # This avoids logging every single connection/disconnection message unless severity is higher
            should_log = (event_type == LogEventType.DATABASE_SLOW_QUERY or 
                          event_name == EVENT_DB_ERROR or 
                          (event_name == EVENT_DB_QUERY and query_text is not None) or # Log actual queries
                          severity.value not in (LogSeverity.INFO.value, LogSeverity.DEBUG.value))
                          
            if should_log:
                log_event(
                    event_type=event_type,
                    event_name=event_name,
                    severity=severity,
                    source=f'parser.postgres.{log_file_name}',
                    message=str(message)[:1000], # Limit message length
                    extra_data={k: v for k, v in extra.items() if v is not None}
                )
                return True
            else:
                logger.debug(f"Skipping generic PG log message: {message[:100]}")
                return False

        except Exception as e:
            logger.error(f"Error formatting PG log entry: {e}. Data: {data}", exc_info=True)
            return False
