from typing import AsyncIterator, Protocol

from app.domain.entities import DownloadProgress


class ProgressStore(Protocol):
    """Порт для публикации/чтения прогресса скачивания. Реализация — Redis.

    Используется и продюсером (celery-задача, через use case) и потребителем
    (SSE-эндпоинт на веб-стороне) — поэтому единый порт, а не два разных.
    """

    async def set_progress(self, progress: DownloadProgress) -> None:
        """Сохранить текущий прогресс и уведомить подписчиков (pub/sub)."""
        ...

    async def get_progress(self, session_id: str) -> DownloadProgress | None:
        ...

    async def subscribe(self, session_id: str) -> AsyncIterator[DownloadProgress]:
        """Асинхронный поток обновлений прогресса для SSE."""
        ...
