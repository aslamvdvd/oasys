# Log Service Application

This Django application (`log_service`) provides a centralized and structured logging system for the OASYS platform.

## Purpose

The primary goal is to capture various events from different parts of the system (application activity, web server access/errors, system logs, database performance, firewall activity) and store them in a consistent, queryable JSON format.

## Features

- **Structured JSON Logging:** All log events are written as individual JSON objects, making them easy to parse and analyze by external tools (e.g., Filebeat, Logstash, Splunk, custom scripts).
- **Categorized Log Types:** Logs are categorized using `LogEventType` (defined in `events.py`), which determines the subdirectory and filename where logs are stored.
- **Daily Log Directories:** Logs are automatically organized into daily directories (`YYYY-MM-DD`).
- **Centralized Logger Function:** The `log_service.logger.log_event` function is the primary interface for logging events from anywhere in the Django application.
- **Event Registry:** An `event_registry.json` file (stored within `LOGS_DIR`) keeps track of all unique event names discovered for each log type, aiding in understanding the logged data.
- **External Log Parsers:** Includes management commands to parse common external log files (Nginx, Syslog, Auth, UFW, PostgreSQL) and ingest them into the structured logging system.
- **State Management for Parsers:** Parsers maintain state (file inode and offset) to handle log rotation and avoid reprocessing already parsed log entries.

## Structure

- `events.py`: Defines `LogEventType` and `LogSeverity` Enums, specific event name constants (e.g., `EVENT_LOGIN`), and functions for managing the `event_registry.json`.
- `logger.py`: Contains the core `log_event` function responsible for formatting and writing log entries to the appropriate JSON file.
- `utils.py`: Utility functions, including checking if the log service is configured.
- `middleware.py`: Example middleware demonstrating how to hook into Django request/response cycle or signals (like `user_logged_out`) to log application-level events.
- `management/commands/`: Contains the log parser commands:
    - `base_parser.py`: Base class providing common state management logic for parsers.
    - `parse_nginx_access.py`: Parses Nginx access logs.
    - `parse_nginx_error.py`: Parses Nginx error logs.
    - `parse_syslog.py`: Parses standard Syslog files.
    - `parse_authlog.py`: Parses Linux authentication logs (auth.log/secure).
    - `parse_ufw.py`: Parses UFW firewall logs.
    - `parse_postgres.py`: Parses PostgreSQL logs (CSV or stderr format).

## Configuration

1.  **`INSTALLED_APPS`**: Ensure `'log_service'` is included in your `INSTALLED_APPS` in `settings.py`.
2.  **`LOGS_DIR`**: You **must** define the `LOGS_DIR` setting in your `settings.py`. This is the base directory where all log files, the event registry, and parser state files will be stored.
    ```python
    # settings.py
    import os
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent
    LOGS_DIR = os.path.join(BASE_DIR, 'logs') # Example: logs directory in project root
    ```
3.  **Log Rotation**: This application organizes logs into daily directories but does **not** include a built-in command for deleting old log files. Log rotation (e.g., deleting files older than 30 days) should be handled by an external system utility like `logrotate` or a custom script targeting the `LOGS_DIR`.

## Usage

### Logging from Application Code

Import `log_event` and `LogEventType`/`LogSeverity`/event constants:

```python
from log_service.logger import log_event
from log_service.events import LogEventType, LogSeverity, EVENT_LOGIN

# Example in a view
def user_login_view(request):
    # ... login logic ...
    if user_logged_in_successfully:
        log_event(
            event_type=LogEventType.USER_ACTIVITY,
            event_name=EVENT_LOGIN,
            severity=LogSeverity.INFO,
            message=f"User '{request.user.username}' logged in successfully.",
            request=request, # Pass request for context (IP, user agent)
            user=request.user,
            extra_data={'login_method': 'password'}
        )
    # ... rest of view ...
```

### Running Log Parsers

Parsers are run as Django management commands. Activate your virtual environment first.

```bash
# Example: Parse Nginx access log
sudo /path/to/venv/bin/python manage.py parse_nginx_access --log-file /var/log/nginx/access.log

# Example: Parse PostgreSQL CSV log
sudo /path/to/venv/bin/python manage.py parse_postgres --log-file /var/log/postgresql/postgresql-16-main.csv --log-format csv --csv-fields <your_field_list>
# Note: For PostgreSQL CSV logs, ensure <your_field_list> matches your 'log_line_prefix' in postgresql.conf.
# Check the DEFAULT_CSV_FIELDS list in the parse_postgres.py command for a common example.

# Example: Parse UFW log
sudo /path/to/venv/bin/python manage.py parse_ufw --log-file /var/log/ufw.log
```

**Note:** Parsers often require `sudo` if reading system log files with restricted permissions. Always use the full path to the Python executable within your virtual environment when using `sudo`.

It is recommended to run these parsers periodically using a scheduler like `cron`.

## Log Format

Log entries are written as single-line JSON objects to files named `<event_type.value>.log` within daily directories (`<LOGS_DIR>/YYYY-MM-DD/`).

A typical log entry includes:

```json
{
  "timestamp": "2023-10-27T12:00:00.123456Z", // UTC timestamp of logging event
  "event_type": "user_activity", // From LogEventType Enum
  "event_name": "login", // Specific event constant or identifier
  "severity": "INFO", // From LogSeverity Enum
  "source": "view.user_login_view", // Originating module/function (usually auto-detected, can be overridden)
  "message": "User 'admin' logged in successfully.", // Human-readable message
  "ip_address": "192.168.1.100", // Extracted from request if available
  "user_agent": "Mozilla/5.0 ...", // Extracted from request if available
  "user_id": 1, // Logged-in user ID if available
  "username": "admin", // Logged-in username if available
  "extra_data": { // Optional dictionary for additional context
    "login_method": "password"
  }
}
``` 