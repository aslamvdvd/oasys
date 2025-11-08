import os
import json
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

# Use Enum and helpers
from log_service.events import LogEventType, get_all_events, get_registry_file_path
from log_service.logger import log_event # Import core log_event

class Command(BaseCommand):
    """
    Management command to check log files, registry, and verify logging.
    """
    help = "Checks log files, event registry, and optionally creates test log entries."

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-test-logs',
            action='store_true',
            help='Create a test log entry for each standard log type',
        )

    def handle(self, *args, **options):
        logs_dir = Path(settings.LOGS_DIR)
        
        if not logs_dir.exists() or not logs_dir.is_dir():
            self.stdout.write(self.style.ERROR(f"Logs directory not found or is not a directory: {logs_dir}"))
            return
            
        self._check_event_registry(logs_dir)
        self._check_log_directories(logs_dir)
        
        if options['create_test_logs']:
            self._create_test_logs()
            
    def _check_event_registry(self, logs_dir):
        """Checks and reports the status of the event registry file."""
        registry_path = get_registry_file_path() # Use helper
        self.stdout.write(self.style.NOTICE(f"\n--- Checking Event Registry ({registry_path}) ---"))
        if registry_path.exists():
            try:
                # Use get_all_events which handles loading and uses Enums internally
                all_event_data = get_all_events()
                self.stdout.write(self.style.SUCCESS("Event registry loaded successfully."))
                self.stdout.write("Registered Log Types & Events:")
                for type_str, data in sorted(all_event_data.items()):
                    events = sorted(data.get('registered_events', []))
                    count = len(events)
                    self.stdout.write(f"  - {type_str}: {count} event(s)")
                    # self.stdout.write(f"    Desc: {data.get('description', 'N/A')}")
                    # self.stdout.write(f"    Events: {', '.join(events) if events else 'None'}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error reading/parsing event registry: {e}"))
        else:
            self.stdout.write(self.style.WARNING("Event registry file not found."))
            
    def _check_log_directories(self, logs_dir):
        """Checks for today's log directory and standard log files within it."""
        self.stdout.write(self.style.NOTICE("\n--- Checking Log Directories & Files ---"))
        today = datetime.now().strftime('%Y-%m-%d')
        today_dir = logs_dir / today
        
        if not today_dir.exists():
            self.stdout.write(self.style.WARNING(f"Today's log directory does not exist: {today_dir}"))
            # Check for the non-dated failures log
            self._check_log_file(logs_dir / 'failures.log')
            return
            
        self.stdout.write(self.style.SUCCESS(f"Today's log directory found: {today_dir}"))
        # Check standard log files derived from LogEventType Enum
        for log_type in LogEventType:
            self._check_log_file(today_dir / f"{log_type.value}.log")
            
        # Check the non-dated failures log
        self._check_log_file(logs_dir / 'failures.log')
        
    def _check_log_file(self, log_path: Path):
        """Checks existence and size of a specific log file."""
        log_name = log_path.name
        if log_path.exists():
            try:
                size = log_path.stat().st_size
                style = self.style.SUCCESS if size > 0 else self.style.WARNING
                status = f"EXISTS ({size} bytes)" + (" (EMPTY)" if size == 0 else "")
                self.stdout.write(style(f"  - {log_name}: {status}"))
            except OSError as e:
                self.stdout.write(self.style.ERROR(f"  - {log_name}: ERROR checking file: {e}"))
        else:
            self.stdout.write(self.style.WARNING(f"  - {log_name}: MISSING"))
            
    def _create_test_logs(self):
        """
        Creates test log entries for standard LogEventTypes.
        """
        self.stdout.write(self.style.NOTICE("\n--- Creating Test Log Entries ---"))
        # Log to standard types, excluding potentially problematic ones if needed
        log_types_to_test = [
            LogEventType.USER_ACTIVITY,
            LogEventType.ADMIN,
            LogEventType.TEMPLATOR,
            # Add others like ENGINE, SPACE_ACTIVITY if they have active logging
        ]
        
        try:
            for log_type_enum in log_types_to_test:
                event_data = {
                    'event': 'test_log',
                    'message': f'Test log entry for {log_type_enum.value}',
                    # timestamp added automatically by log_event
                }
                log_event(log_type_enum, event_data)
                self.stdout.write(self.style.SUCCESS(f"  - Logged test event to {log_type_enum.value}.log"))
                
            self.stdout.write(self.style.SUCCESS("\nTest log creation finished."))
            self.stdout.write("Run command again without --create-test-logs to verify.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating test logs: {e}")) 