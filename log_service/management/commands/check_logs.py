import os
import json
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    """
    Management command to check log files and verify logging functionality.
    """
    help = "Checks log files and verifies that logging is functioning properly"

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-test-logs',
            action='store_true',
            help='Create test log entries for each log type',
        )

    def handle(self, *args, **options):
        # Get the logs directory
        logs_dir = Path(settings.LOGS_DIR)
        
        # Check if the logs directory exists
        if not logs_dir.exists():
            self.stdout.write(self.style.ERROR(f"Logs directory {logs_dir} does not exist."))
            return
        
        # Report on the event registry
        registry_path = logs_dir / 'event_registry.json'
        if registry_path.exists():
            try:
                with open(registry_path, 'r') as f:
                    registry_data = json.load(f)
                
                self.stdout.write(self.style.SUCCESS(f"Event registry found at {registry_path}"))
                self.stdout.write("Registered log types:")
                
                for log_type, data in registry_data.items():
                    events = data.get('registered_events', [])
                    self.stdout.write(f"  - {log_type}: {len(events)} events registered")
                    self.stdout.write(f"    Description: {data.get('description', 'No description')}")
                    self.stdout.write(f"    Events: {', '.join(sorted(events))}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error reading event registry: {str(e)}"))
        else:
            self.stdout.write(self.style.WARNING(f"Event registry not found at {registry_path}"))
        
        # Check for today's log directory
        today = datetime.now().strftime('%Y-%m-%d')
        today_dir = logs_dir / today
        
        if today_dir.exists():
            self.stdout.write(self.style.SUCCESS(f"Today's log directory exists: {today_dir}"))
            
            # Check for specific log files
            log_files = ['user_activity.log', 'admin.log', 'templator.log', 'failures.log']
            for log_file in log_files:
                log_path = today_dir / log_file if log_file != 'failures.log' else logs_dir / log_file
                
                if log_path.exists():
                    size = log_path.stat().st_size
                    self.stdout.write(f"  - {log_file}: EXISTS ({size} bytes)")
                    
                    # If it's empty, that might be a problem
                    if size == 0:
                        self.stdout.write(self.style.WARNING(f"    Warning: {log_file} is empty"))
                else:
                    self.stdout.write(self.style.WARNING(f"  - {log_file}: MISSING"))
        else:
            self.stdout.write(self.style.WARNING(f"Today's log directory does not exist: {today_dir}"))
        
        # Create test logs if requested
        if options['create_test_logs']:
            self.create_test_logs()
    
    def create_test_logs(self):
        """
        Create test log entries for each log type.
        """
        try:
            from log_service import log_event
            
            log_types = ['user_activity', 'admin', 'templator']
            
            for log_type in log_types:
                log_event(log_type, {
                    'event': 'test_log',
                    'message': f'Test log entry for {log_type}',
                    'timestamp': datetime.now().isoformat()
                })
            
            self.stdout.write(self.style.SUCCESS("Created test log entries for each log type."))
            self.stdout.write("Run this command again without --create-test-logs to verify they were created.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating test logs: {str(e)}")) 