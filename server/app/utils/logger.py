from enum import Enum
import logging
import logging.config

from app.config import settings


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


LOG_LEVEL = LogLevel(settings.LOG_LEVEL) or LogLevel.INFO


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "colored": {
            "()": "colorlog.ColoredFormatter",
            "format": "%(asctime)s - %(name)s - %(log_color)s%(levelname)s%(reset)s - %(message)s",
            "log_colors": {
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        },
    },
    "handlers": {
        "default": {
            "formatter": "colored",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": LOG_LEVEL.value,
        "handlers": ["default"],
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": LOG_LEVEL.value, "propagate": False},
        "uvicorn.error": {"level": LOG_LEVEL.value},
        "uvicorn.access": {"level": LOG_LEVEL.value},
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
