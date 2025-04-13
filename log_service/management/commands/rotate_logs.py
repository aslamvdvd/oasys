import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """
    Management command to rotate (delete) old log files.
    """
    help = "Deletes log files older than the specified number of days"

    def add_arguments(self, parser):
        parser.add_argument('days', type=int, help='Number of days to keep logs for')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the deletion process without actually removing any files',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        if days < 1:
            raise CommandError('Number of days must be at least 1')
        
        logs_dir = Path(settings.LOGS_DIR)
        if not logs_dir.exists():
            self.stdout.write(self.style.WARNING(f'Logs directory {logs_dir} does not exist. Nothing to rotate.'))
            return
        
        # Calculate the cutoff date
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        self.stdout.write(f"Looking for log directories older than {cutoff_str}...")
        
        deleted_count = 0
        total_size_bytes = 0
        
        # Process each date directory in the logs folder
        for item in logs_dir.iterdir():
            # Skip the failures.log file and non-directories
            if item.name == 'failures.log' or not item.is_dir():
                continue
            
            try:
                # Try to parse the directory name as a date
                dir_date = datetime.strptime(item.name, '%Y-%m-%d')
                
                # If the directory date is older than the cutoff, delete it
                if dir_date.date() < cutoff_date.date():
                    # Calculate the size of the directory
                    dir_size = sum(f.stat().st_size for f in item.glob('**/*') if f.is_file())
                    total_size_bytes += dir_size
                    
                    if dry_run:
                        self.stdout.write(f"Would delete: {item} ({dir_size} bytes)")
                    else:
                        shutil.rmtree(item)
                        self.stdout.write(f"Deleted: {item} ({dir_size} bytes)")
                    
                    deleted_count += 1
            except ValueError:
                # If the directory name isn't a valid date format, skip it
                self.stdout.write(self.style.WARNING(f"Skipping non-date directory: {item}"))
                continue
        
        # Convert total size to a human-readable format
        total_size = self._format_size(total_size_bytes)
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Dry run completed. Would have deleted {deleted_count} log directories ({total_size}).")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Log rotation completed. Deleted {deleted_count} log directories ({total_size}).")
            )
    
    def _format_size(self, size_bytes):
        """
        Format a size in bytes as a human-readable string.
        """
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB" 