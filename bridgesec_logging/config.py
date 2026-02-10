"""
Centralized logging configuration for BridgeSec microservices.
Sets up structured JSON logging with Loki integration.
"""

import logging
import logging.config
import os
import socket
from pathlib import Path

# Try to import LokiHandler, but gracefully handle if not installed
try:
    from logging_loki import LokiHandler
    LOKI_AVAILABLE = True
except ImportError:
    LOKI_AVAILABLE = False
    logging.warning("python-logging-loki not installed. Loki integration disabled.")


class ContextFilter(logging.Filter):
    """
    Add contextual information to log records.
    This allows us to include request_id, user, entity_type, etc. in logs.
    """

    def __init__(self, hostname, environment):
        super().__init__()
        self.hostname = hostname
        self.environment = environment

    def filter(self, record):
        # Add default values if not already present
        if not hasattr(record, 'request_id'):
            record.request_id = 'N/A'
        if not hasattr(record, 'user'):
            record.user = 'system'
        if not hasattr(record, 'component'):
            record.component = 'unknown'
        if not hasattr(record, 'entity_type'):
            record.entity_type = 'N/A'
        if not hasattr(record, 'duration_ms'):
            record.duration_ms = 0
        if not hasattr(record, 'operation'):
            record.operation = 'N/A'
        if not hasattr(record, 'resource_count'):
            record.resource_count = 0

        # Add hostname and environment
        record.hostname = self.hostname
        record.environment = self.environment

        return True


def setup_logging(
    app_name='bridgesec',
    log_dir=None,
    environment=None,
    loki_url=None,
    log_level='INFO',
    enable_console=True,
    enable_file=True,
    enable_loki=True,
    max_bytes=10485760,  # 10MB
    backup_count=5,
):
    """
    Configure logging for the application.

    Args:
        app_name: Name of the application (used in Loki tags)
        log_dir: Directory to write log files (Path object or string)
        environment: Environment name (development, production, etc.)
        loki_url: Loki server URL for log aggregation
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_console: Enable console logging
        enable_file: Enable file logging
        enable_loki: Enable Loki integration
        max_bytes: Maximum bytes per log file before rotation
        backup_count: Number of backup log files to keep

    Usage:
        from bridgesec_logging import setup_logging
        setup_logging(
            app_name="bridgesec",
            log_dir=Path("/var/log/bridgesec"),
            environment="production"
        )
    """

    # Get defaults from environment if not provided
    if environment is None:
        environment = os.getenv('ENVIRONMENT', 'development')
    if loki_url is None:
        loki_url = os.getenv('LOKI_URL', 'http://localhost:3100/loki/api/v1/push')

    # Get hostname
    hostname = socket.gethostname()

    # Determine log directory
    if log_dir is None:
        # Try to get from Django settings
        try:
            from django.conf import settings
            BASE_DIR = getattr(settings, 'BASE_DIR', Path.cwd())
            log_dir = BASE_DIR / 'logs'
        except:
            log_dir = Path.cwd() / 'logs'
    else:
        log_dir = Path(log_dir)

    # Ensure logs directory exists
    log_dir.mkdir(exist_ok=True, parents=True)

    # Create context filter instance
    context_filter = ContextFilter(hostname, environment)

    # Build logging configuration
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'filters': {
            'context_filter': {
                '()': lambda: context_filter,
            },
        },
        'formatters': {
            'json': {
                '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(user)s %(component)s %(entity_type)s %(operation)s %(duration_ms)s %(resource_count)s %(hostname)s %(environment)s',
                'datefmt': '%Y-%m-%dT%H:%M:%S',
            },
            'detailed': {
                'format': '[%(asctime)s] [%(levelname)s] [%(name)s] [%(request_id)s] %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
            'simple': {
                'format': '%(levelname)s - %(message)s',
            },
        },
        'handlers': {},
        'loggers': {
            'django': {
                'handlers': [],
                'level': log_level,
                'propagate': False,
            },
            'celery': {
                'handlers': [],
                'level': log_level,
                'propagate': False,
            },
            'core': {
                'handlers': [],
                'level': log_level,
                'propagate': False,
            },
            'entities': {
                'handlers': [],
                'level': log_level,
                'propagate': False,
            },
            'terraform_workflow': {
                'handlers': [],
                'level': log_level,
                'propagate': False,
            },
        },
        'root': {
            'level': log_level,
            'handlers': [],
        },
    }

    # Add console handler if enabled
    if enable_console:
        LOGGING_CONFIG['handlers']['console'] = {
            'class': 'logging.StreamHandler',
            'level': log_level,
            'formatter': 'detailed',
            'filters': ['context_filter'],
        }
        for logger_name in LOGGING_CONFIG['loggers']:
            LOGGING_CONFIG['loggers'][logger_name]['handlers'].append('console')
        LOGGING_CONFIG['root']['handlers'].append('console')

    # Add file handlers if enabled
    if enable_file:
        LOGGING_CONFIG['handlers']['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': log_level,
            'formatter': 'json',
            'filters': ['context_filter'],
            'filename': str(log_dir / f'{app_name}.log'),
            'maxBytes': max_bytes,
            'backupCount': backup_count,
        }

        # Add celery-specific log file
        LOGGING_CONFIG['handlers']['celery_file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': log_level,
            'formatter': 'json',
            'filters': ['context_filter'],
            'filename': str(log_dir / f'{app_name}_celery.log'),
            'maxBytes': max_bytes,
            'backupCount': backup_count,
        }

        # Assign file handlers to loggers
        for logger_name in ['django', 'core', 'entities', 'terraform_workflow']:
            LOGGING_CONFIG['loggers'][logger_name]['handlers'].append('file')

        LOGGING_CONFIG['loggers']['celery']['handlers'].append('celery_file')
        LOGGING_CONFIG['root']['handlers'].append('file')

    # Apply configuration
    logging.config.dictConfig(LOGGING_CONFIG)

    # Add Loki handler if enabled and available
    if enable_loki and loki_url and LOKI_AVAILABLE:
        try:
            loki_handler = LokiHandler(
                url=loki_url,
                tags={
                    "app": app_name,
                    "environment": environment,
                    "hostname": hostname,
                },
                version="1",
            )
            loki_handler.setLevel(logging.INFO)
            loki_handler.addFilter(context_filter)

            # Add Loki handler to root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(loki_handler)

            logging.info(f"Loki handler configured successfully: {loki_url}")
        except Exception as e:
            logging.warning(f"Failed to configure Loki handler: {e}")
    elif loki_url and not LOKI_AVAILABLE:
        logging.warning("Loki URL configured but python-logging-loki not installed")

    logging.info(f"{app_name} logging configured successfully (environment={environment})")


def get_logger(name):
    """
    Get a logger instance with the given name.

    Usage:
        from bridgesec_logging import get_logger
        logger = get_logger(__name__)
        logger.info("Message", extra={'request_id': '123', 'user': 'john'})
    """
    return logging.getLogger(name)
