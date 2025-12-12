import logging
import logging.config
from typing import Any


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
