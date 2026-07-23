from __future__ import annotations

import asyncio
import logging

from dishka import AsyncContainer, make_async_container

from app.application.use_cases.download_catalog import DownloadCatalogUseCase
from app.celery_app import celery_app, settings
from app.di import get_providers

logger = logging.getLogger(__name__)

_worker_container: AsyncContainer | None = None


def _get_worker_container() -> AsyncContainer:
    """Единый APP-scope DI-контейнер на процесс воркера.

    Celery-задача не занимается сборкой зависимостей вручную — контейнер
    создаётся один раз на процесс, а на каждый вызов задачи открывается
    свой REQUEST-scope (см. execute_download).
    """

    global _worker_container
    if _worker_container is None:
        _worker_container = make_async_container(*get_providers(), context={type(settings): settings})
    return _worker_container


async def _execute_download(session_id: str) -> None:
    container = _get_worker_container()
    async with container() as request_container:
        use_case = await request_container.get(DownloadCatalogUseCase)
        await use_case.execute(session_id)


@celery_app.task(name="download_catalog", bind=True, max_retries=0)
def download_catalog_task(self, session_id: str) -> None:  # noqa: ANN001 - celery task signature
    """Celery-задача — только точка входа. Вся бизнес-логика в use case.

    Повторы при ошибках внешнего API (429/403) обрабатываются ВНУТРИ
    DownloadCatalogUseCase (там своя логика ожидания Retry-After), поэтому
    у самой celery-задачи retry не настроен — падение здесь означает
    действительно необработанную ошибку, которую нужно смотреть в логах.
    """

    logger.info("celery task download_catalog started: session_id=%s", session_id)
    try:
        asyncio.run(_execute_download(session_id))
    except Exception:
        logger.exception("celery task download_catalog failed: session_id=%s", session_id)
        raise
