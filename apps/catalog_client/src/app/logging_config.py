import logging
import logging.config

from app.config import Settings


def configure_logging(settings: Settings) -> None:
    """Настраивает логирование для всего приложения (web-процесс и celery worker)."""

    formatter: dict
    if settings.log_json:
        formatter = {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    else:
        formatter = {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        }

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"default": formatter},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                }
            },
            "root": {"handlers": ["console"], "level": settings.log_level},
            "loggers": {
                "uvicorn": {"level": settings.log_level, "propagate": True},
                "celery": {"level": settings.log_level, "propagate": True},
                "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
                "httpx": {"level": "WARNING", "propagate": True},
                "app": {"level": settings.log_level, "propagate": True},
            },
        }
    )
