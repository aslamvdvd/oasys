"""
Enums for log service event types and log levels.
"""

from enum import Enum, unique

@unique
class EventType(Enum):
    """Categorizes log events, corresponding to log file names/types."""
    USER_ACTIVITY = 'user_activity'
    ADMIN = 'admin'
    APPLICATION = 'application'
    SERVER_ACCESS = 'server_access'
    SERVER_ERROR = 'server_error'
    SYSTEM_AUTH = 'system_auth'
    SYSTEM_SYSLOG = 'system_syslog'
    DATABASE = 'database'
    DATABASE_SLOW_QUERY = 'database_slow_query'
    FIREWALL = 'firewall'
    TEMPLATOR = 'templator'
    TEMPLATOR_ACTIVITY = 'templator_activity'

@unique
class LogLevel(Enum):
    """Standard log severity levels."""
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL' 