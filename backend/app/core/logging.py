import logging
import logging.config
from typing import Any
import json


class StructuredFormatter(logging.Formatter):
    """Custom formatter that includes extra fields as JSON."""

    RESERVED_ATTRS = {
        'name', 'msg', 'args', 'created', 'filename', 'funcName', 'levelname',
        'levelno', 'lineno', 'module', 'msecs', 'pathname', 'process',
        'processName', 'relativeCreated', 'thread', 'threadName', 'exc_info',
        'exc_text', 'stack_info', 'asctime', 'message', 'relativeCreated'
    }

    def format(self, record: logging.LogRecord) -> str:
        # Get base formatted message
        base_message = super().format(record)

        # Extract extra fields (anything not in reserved attributes)
        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self.RESERVED_ATTRS
        }

        # If there are extra fields, append them as JSON
        if extra_fields:
            extra_json = json.dumps(extra_fields, default=str)
            return f"{base_message} | {extra_json}"

        return base_message


def configure_logging(settings: Any) -> None:
    """Configure structured logging for the application."""

    # Check if already configured
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": "app.core.logging.StructuredFormatter",
                "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "structured",
                "stream": "ext://sys.stdout"
            }
        },
        "root": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console"]
        }
    }

    logging.config.dictConfig(config)

def setup_logging() -> None:
    """Setup application logging"""
    from app.core.config import settings
    configure_logging(settings)
