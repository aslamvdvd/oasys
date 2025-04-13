import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings

from log_service.logger import log_event, _log_failure


class LogServiceTestCase(TestCase):
    """
    Tests for the log_service app functionality.
    """
    
    def setUp(self):
        """
        Create a temporary directory for logs during tests.
        """
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """
        Clean up the temporary directory after tests.
        """
        shutil.rmtree(self.temp_dir)
    
    @override_settings(LOGS_DIR=None)
    @patch('log_service.logger._log_failure')
    def test_log_event_with_invalid_logs_dir(self, mock_log_failure):
        """
        Test that logging fails gracefully when LOGS_DIR is not properly set.
        """
        # Ensure LOGS_DIR is None for this test (via the override_settings decorator)
        
        data = {'event': 'login', 'user_id': 1}
        log_event('user_activity', data)
        
        # Check that _log_failure was called
        mock_log_failure.assert_called()
    
    @override_settings()
    def test_log_event_creates_directories(self):
        """
        Test that log_event creates the date-based directory structure.
        """
        # Override settings to use our temp directory
        with self.settings(LOGS_DIR=self.temp_dir):
            data = {'event': 'login', 'user_id': 1}
            log_event('user_activity', data)
            
            # Check if the directory was created
            today = datetime.now().strftime('%Y-%m-%d')
            expected_dir = Path(self.temp_dir) / today
            self.assertTrue(expected_dir.exists(), f"Directory {expected_dir} was not created")
            
            # Check if the log file was created
            expected_file = expected_dir / 'user_activity.log'
            self.assertTrue(expected_file.exists(), f"Log file {expected_file} was not created")
    
    @override_settings()
    def test_log_event_writes_json(self):
        """
        Test that log_event writes proper JSON data to the log file.
        """
        # Override settings to use our temp directory
        with self.settings(LOGS_DIR=self.temp_dir):
            data = {'event': 'login', 'user_id': 1, 'details': 'Test login'}
            log_event('user_activity', data)
            
            # Read the log file
            today = datetime.now().strftime('%Y-%m-%d')
            log_file = Path(self.temp_dir) / today / 'user_activity.log'
            
            with open(log_file, 'r') as f:
                log_content = f.read().strip()
            
            # Parse the JSON and verify the content
            parsed_log = json.loads(log_content)
            self.assertEqual(parsed_log['event'], 'login')
            self.assertEqual(parsed_log['user_id'], 1)
            self.assertEqual(parsed_log['details'], 'Test login')
            self.assertIn('timestamp', parsed_log)
    
    @override_settings()
    def test_log_event_with_invalid_type(self):
        """
        Test that log_event properly handles invalid log types.
        """
        # Override settings to use our temp directory
        with self.settings(LOGS_DIR=self.temp_dir):
            data = {'event': 'test', 'details': 'Should not be logged'}
            log_event('invalid_type', data)
            
            # Check that a fallback log was created
            fallback_log = Path(self.temp_dir) / 'failures.log'
            self.assertTrue(fallback_log.exists(), "Fallback log file was not created")
            
            # Verify the content includes the invalid type
            with open(fallback_log, 'r') as f:
                fallback_content = f.read()
            
            self.assertIn('invalid_type', fallback_content)
    
    @override_settings()
    def test_multiple_log_types(self):
        """
        Test logging to multiple different log types.
        """
        # Override settings to use our temp directory
        with self.settings(LOGS_DIR=self.temp_dir):
            # Log to different log types
            log_event('user_activity', {'event': 'login', 'user_id': 1})
            log_event('space_activity', {'event': 'create', 'space_id': 100})
            log_event('social_media', {'event': 'share', 'content_id': 200})
            log_event('engine', {'event': 'process', 'job_id': 300})
            
            # Check if all log files were created
            today = datetime.now().strftime('%Y-%m-%d')
            daily_dir = Path(self.temp_dir) / today
            
            for log_type in ['user_activity', 'space_activity', 'social_media', 'engine']:
                log_file = daily_dir / f"{log_type}.log"
                self.assertTrue(log_file.exists(), f"Log file {log_file} was not created")
    
    @override_settings()
    @patch('log_service.logger.open', side_effect=PermissionError("Permission denied"))
    @patch('logging.error')
    def test_fallback_logging_failure(self, mock_logging_error, mock_open):
        """
        Test that the system handles failures in the fallback logging mechanism.
        """
        # Override settings to use our temp directory
        with self.settings(LOGS_DIR=self.temp_dir):
            # This should trigger the logging.error fallback since _log_failure will fail
            _log_failure("Test error message", {'test': 'data'})
            
            # Check that logging.error was called
            mock_logging_error.assert_called()
