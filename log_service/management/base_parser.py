"""
Base class for log parsing management commands providing common state handling.
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

logger = logging.getLogger(__name__)

class BaseLogParserCommand(BaseCommand):
    """
    Base command for parsing log files with state management (inode, offset).

    Subclasses should implement:
        - `handle()` method for the main parsing logic.
        - Define `parser_name` (e.g., 'nginx_access', 'syslog') used for state file naming.
        - Define `log_event_type` (e.g., LogEventType.SERVER_ACCESS).
        - Define `log_parser_re` (the regex for parsing log lines).
        - Implement `_process_log_entry(self, parsed_data, log_file_name, original_line, ...)`
    
    The handle method should typically:
        1. Call `self._setup_paths_and_logger(options)`.
        2. Call `self._load_state()`.
        3. Open the log file and seek to `self.start_offset`.
        4. Loop through lines, parse using `self.log_parser_re`, call `_process_log_entry`.
        5. Update `self.last_offset`.
        6. Call `self._save_state()` at the end or in error handling.
    """
    # --- Attributes to be set by subclasses or handle() ---
    parser_name: str = "base_parser" # Needs override in subclass
    log_file_path: Path = None
    state_file_path: Path = None
    state_dir: Path = None
    current_inode: int = None
    start_offset: int = 0
    last_offset: int = 0

    def add_arguments(self, parser):
        """Adds common arguments for log file path and state directory."""
        parser.add_argument(
            '--log-file', 
            type=str,
            required=True,
            help='Path to the log file to parse.'
        )
        parser.add_argument(
            '--state-dir',
            type=str,
            default=None,
            help='Directory to store state files (defaults to LOGS_DIR/parser_state/).'
        )
        # Subclasses can add more arguments like --format-name

    def _setup_paths_and_logger(self, options: dict):
        """Validates paths and sets up file/state paths based on options."""
        log_file_path_str = options['log_file']
        state_dir_str = options['state_dir']

        self.log_file_path = Path(log_file_path_str).resolve()
        
        if not self.log_file_path.is_file():
            raise CommandError(f"Log file not found or is not a file: {self.log_file_path}")

        # Determine state directory
        if state_dir_str:
            self.state_dir = Path(state_dir_str).resolve()
        else:
            log_dir_base = getattr(settings, 'LOGS_DIR', None)
            if not log_dir_base:
                 raise CommandError("LOGS_DIR setting is not configured and --state-dir was not provided.")
            self.state_dir = Path(log_dir_base) / 'parser_state'
            
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise CommandError(f"Could not create state directory {self.state_dir}: {e}")

        # Generate state file name using parser_name attribute
        state_file_hash = hashlib.md5(str(self.log_file_path).encode()).hexdigest()
        self.state_file_path = self.state_dir / f"{self.parser_name}_{state_file_hash}.json"
        
        self.stdout.write(f"Processing log file: {self.log_file_path}")
        self.stdout.write(f"Using state file: {self.state_file_path}")
        
    def _load_state(self) -> None:
        """Loads state (inode, offset) from the state file and sets attributes."""
        if not self.state_file_path or not self.log_file_path:
             raise CommandError("State file path or log file path not set before loading state.")
             
        start_offset = 0
        last_inode = None
        try:
            if self.state_file_path.exists():
                with open(self.state_file_path, 'r') as f:
                    state_data = json.load(f)
                last_inode = state_data.get('inode')
                last_offset = state_data.get('offset', 0)
                logger.debug(f"Loaded state: inode={last_inode}, offset={last_offset}")
            else:
                logger.info("State file not found, starting from beginning.")
        except (json.JSONDecodeError, IOError, Exception) as e:
            logger.warning(f"Could not load state file {self.state_file_path}, starting from beginning. Error: {e}")
            last_inode = None
            last_offset = 0
        
        try:
            current_stat = os.stat(self.log_file_path)
            current_inode = current_stat.st_ino
            current_size = current_stat.st_size
        except FileNotFoundError:
             raise CommandError(f"Log file not found when checking status: {self.log_file_path}")
        except PermissionError:
             raise CommandError(f"Permission denied accessing log file stats: {self.log_file_path}")

        if last_inode is not None and last_inode == current_inode:
            if last_offset <= current_size:
                start_offset = last_offset
                logger.info(f"Resuming from offset {start_offset} (inode matched)")
            else:
                logger.warning(f"Stored offset {last_offset} > current size {current_size}. Assuming truncation, starting from beginning.")
                start_offset = 0
        else:
            if last_inode is not None:
                 logger.info(f"Inode changed (was {last_inode}, now {current_inode}). Assuming log rotation, starting from beginning.")
            start_offset = 0
            
        self.current_inode = current_inode
        self.start_offset = start_offset
        self.last_offset = start_offset # Initialize last_offset

    def _save_state(self):
        """Saves the current inode and last offset to the state file."""
        if self.current_inode is None or self.last_offset is None or not self.state_file_path:
            logger.error("Cannot save state - inode, offset, or state_file_path not set.")
            return
            
        state_data = {'inode': self.current_inode, 'offset': self.last_offset}
        try:
            # Atomic write
            temp_path = self.state_file_path.with_suffix(f'.tmp_{os.getpid()}')
            with open(temp_path, 'w') as f:
                json.dump(state_data, f)
            os.rename(temp_path, self.state_file_path)
            logger.debug(f"Saved state: inode={self.current_inode}, offset={self.last_offset}")
        except (IOError, OSError, Exception) as e:
            logger.error(f"Failed to save state file {self.state_file_path}: {e}")

    def handle(self, *args, **options):
        """Placeholder handle method. Subclasses must implement the actual parsing loop."""
        raise NotImplementedError("Subclasses of BaseLogParserCommand must implement a handle() method.") 