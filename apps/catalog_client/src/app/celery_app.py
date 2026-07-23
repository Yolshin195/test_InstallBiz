from celery import Celery

from app.config import get_settings
from app.logging_config import configure_logging

settings = get_settings()
configure_logging(settings)

celery_app = Celery(
    "file_stats_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.adapters.inbound.celery_tasks.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Задача скачивания может идти долго (десятки/сотни запросов с ретраями) —
    # не хотим, чтобы воркер её убил по таймауту раньше времени.
    task_time_limit=60 * 60,
    task_soft_time_limit=55 * 60,
    worker_prefetch_multiplier=1,
)
