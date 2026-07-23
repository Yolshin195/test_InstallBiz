from __future__ import annotations

from typing import AsyncIterator

from app.domain.entities import DownloadProgress
from app.domain.ports.progress_store import ProgressStore


class GetProgressUseCase:
    """Отдаёт текущий и последующие снимки прогресса скачивания (для SSE)."""

    def __init__(self, progress_store: ProgressStore) -> None:
        self._progress_store = progress_store

    async def current(self, session_id: str) -> DownloadProgress | None:
        return await self._progress_store.get_progress(session_id)

    async def stream(self, session_id: str) -> AsyncIterator[DownloadProgress]:
        async for progress in self._progress_store.subscribe(session_id):
            yield progress
