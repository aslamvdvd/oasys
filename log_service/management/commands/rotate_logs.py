import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Management command to rotate (delete) old log directories.
    Skips the central 'failures.log' and 'event_registry.json'.
    """
    help = "Deletes daily log directories older than the specified number of days."

    def add_arguments(self, parser):
        parser.add_argument(
            'days', 
            type=int, 
            help='Number of days of logs to keep (e.g., 30 keeps logs from the last 30 days)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the deletion process without actually removing directories'
        )

    def handle(self, *args, **options):
        days_to_keep = options['days']
        dry_run = options['dry_run']
        
        if days_to_keep < 1:
            raise CommandError('Number of days to keep must be at least 1.')
        
        logs_dir = Path(settings.LOGS_DIR)
        if not logs_dir.is_dir():
            self.stdout.write(self.style.WARNING(f'Logs directory not found: {logs_dir}. Nothing to rotate.'))
            return
        
        # Calculate the first date to *keep* (inclusive)
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).date()
        
        self.stdout.write(f"Rotating logs in: {logs_dir}")
        self.stdout.write(f"Keeping logs from {cutoff_date.strftime('%Y-%m-%d')} onwards.")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: No directories will actually be deleted."))
            
        deleted_count = 0
        total_size_bytes = 0
        skipped_count = 0
        error_count = 0
        
        # Iterate through items in the logs directory
        for item in logs_dir.iterdir():
            # Only consider directories whose names look like dates
            if item.is_dir() and self._is_valid_date_dir(item.name):
                try:
                    dir_date = datetime.strptime(item.name, '%Y-%m-%d').date()
                    
                    # Delete if the directory date is *before* the cutoff date
                    if dir_date < cutoff_date:
                        dir_size = self._get_dir_size(item)
                        total_size_bytes += dir_size
                        size_str = self._format_size(dir_size)
                        
                        if dry_run:
                            self.stdout.write(f"[DRY RUN] Would delete: {item.name} ({size_str})")
                        else:
                            try:
                                shutil.rmtree(item)
                                self.stdout.write(f"Deleted: {item.name} ({size_str})")
                            except OSError as delete_err:
                                self.stderr.write(self.style.ERROR(f"Error deleting directory {item.name}: {delete_err}"))
                                error_count += 1
                                continue # Skip incrementing deleted_count
                                
                        deleted_count += 1
                except ValueError:
                    # Should be caught by _is_valid_date_dir, but handle defensively
                    self.stdout.write(self.style.WARNING(f"Skipping directory with unexpected name format: {item.name}"))
                    skipped_count += 1
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error processing directory {item.name}: {e}"))
                    error_count += 1
            # Explicitly skip the parser_state directory and known files
            elif item.name in ['parser_state', 'failures.log', 'event_registry.json']:
                 logger.debug(f"Skipping known item: {item.name}")
                 skipped_count += 1 # Optionally count these as skipped
                 continue
            # Log other unexpected files/items found
            elif not item.is_dir():
                 logger.warning(f"Found unexpected file in logs directory: {item.name}")
                 skipped_count += 1
            else: # Log other unexpected directories
                 logger.warning(f"Found unexpected directory in logs directory: {item.name}")
                 skipped_count += 1
                 
        # Final summary
        total_size_str = self._format_size(total_size_bytes)
        summary_msg = (
            f"Rotation complete. {deleted_count} director(y/ies) deleted ({total_size_str}). "
            f"{skipped_count} item(s) skipped. {error_count} error(s)."
        )
        if dry_run:
             summary_msg = (
                 f"Dry run complete. Would have deleted {deleted_count} director(y/ies) ({total_size_str}). "
                 f"{skipped_count} item(s) skipped."
             )
             
        if error_count > 0:
             self.stdout.write(self.style.ERROR(summary_msg))
        else:
             self.stdout.write(self.style.SUCCESS(summary_msg))

    def _is_valid_date_dir(self, dir_name: str) -> bool:
        """Check if a directory name matches the YYYY-MM-DD format."""
        try:
            datetime.strptime(dir_name, '%Y-%m-%d')
            return True
        except ValueError:
            return False
            
    def _get_dir_size(self, path: Path) -> int:
        """Calculate the total size of a directory."""
        total = 0
        try:
            for entry in path.rglob('*'): # Use rglob for recursive size
                if entry.is_file():
                    try:
                        total += entry.stat().st_size
                    except OSError:
                         logger.warning(f"Could not get size for file: {entry}")
        except OSError as e:
             logger.error(f"Could not calculate size for directory {path}: {e}")
        return total

    def _format_size(self, size_bytes: int) -> str:
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