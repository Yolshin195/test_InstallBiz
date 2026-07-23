from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.domain.entities import DownloadedFile, DownloadProgress, DownloadStatus
from app.domain.exceptions import (
    FilesNotFoundError,
    RateLimitedError,
    TemporarilyBlockedError,
)
from app.domain.ports.file_catalog_client import FileCatalogClient
from app.domain.ports.file_repository import FileRepository
from app.domain.ports.progress_store import ProgressStore

logger = logging.getLogger(__name__)

MAX_FILES_PER_DOWNLOAD_REQUEST = 3
MAX_RETRIES_PER_STEP = 8


class DownloadCatalogUseCase:
    """Бизнес-логика полного скачивания каталога файлов.

    Работает до тех пор, пока GET /api/files/names не вернёт пустой список.
    Вся логика повторов при 429/430(бане) и сохранения прогресса живёт здесь,
    а не в Celery-задаче — задача лишь вызывает execute().
    """

    def __init__(
        self,
        catalog_client: FileCatalogClient,
        file_repository: FileRepository,
        progress_store: ProgressStore,
    ) -> None:
        self._catalog_client = catalog_client
        self._file_repository = file_repository
        self._progress_store = progress_store

    async def execute(self, session_id: str) -> None:
        progress = DownloadProgress(
            session_id=session_id,
            status=DownloadStatus.RUNNING,
            started_at=datetime.now(tz=timezone.utc),
        )
        await self._progress_store.set_progress(progress)
        logger.info("download session %s started", session_id)

        try:
            while True:
                names = await self._get_names_resilient()
                if not names:
                    break

                # Не скачиваем повторно то, что уже есть у нас в базе
                # (на случай, если процесс перезапускался и часть уже сохранена).
                already = await self._file_repository.existing_names(names)
                to_download = [n for n in names if n not in already]

                progress.total_known += len(names)
                progress.downloaded += len(already)
                await self._progress_store.set_progress(progress)

                for i in range(0, len(to_download), MAX_FILES_PER_DOWNLOAD_REQUEST):
                    batch = to_download[i : i + MAX_FILES_PER_DOWNLOAD_REQUEST]
                    if not batch:
                        continue
                    content_map = await self._download_resilient(batch)
                    files = [
                        DownloadedFile(
                            name=name,
                            content=content,
                            downloaded_at=datetime.now(tz=timezone.utc),
                        )
                        for name, content in content_map.items()
                    ]
                    await self._file_repository.save_many(files)
                    await self._mark_downloaded_resilient(batch)

                    progress.downloaded += len(batch)
                    await self._progress_store.set_progress(progress)
                    logger.info(
                        "session %s: downloaded %d/%d",
                        session_id,
                        progress.downloaded,
                        progress.total_known,
                    )

            progress.status = DownloadStatus.COMPLETED
            progress.finished_at = datetime.now(tz=timezone.utc)
            await self._progress_store.set_progress(progress)
            logger.info("download session %s completed: %d files", session_id, progress.downloaded)

        except Exception as exc:  # noqa: BLE001 - хотим сохранить любую ошибку в прогресс
            progress.status = DownloadStatus.ERROR
            progress.finished_at = datetime.now(tz=timezone.utc)
            progress.message = str(exc)
            await self._progress_store.set_progress(progress)
            logger.exception("download session %s failed", session_id)
            raise

    async def _get_names_resilient(self) -> list[str]:
        try:
            return await self._with_retries(self._catalog_client.get_names)
        except FilesNotFoundError:
            return []

    async def _download_resilient(self, batch: list[str]) -> dict[str, str]:
        try:
            return await self._with_retries(lambda: self._catalog_client.download(batch))
        except FilesNotFoundError as exc:
            # Файл мог исчезнуть из каталога между get_names и download — пропускаем пачку.
            logger.warning("files not found, skipping batch %s: %s", batch, exc)
            return {}

    async def _mark_downloaded_resilient(self, batch: list[str]) -> None:
        try:
            await self._with_retries(lambda: self._catalog_client.mark_downloaded(batch))
        except FilesNotFoundError as exc:
            logger.warning("mark_downloaded: files not found %s: %s", batch, exc)

    @staticmethod
    async def _with_retries(action):
        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES_PER_STEP + 1):
            try:
                return await action()
            except RateLimitedError as exc:
                last_error = exc
                logger.warning("rate limited, sleeping %.1fs (attempt %d)", exc.retry_after, attempt)
                await asyncio.sleep(exc.retry_after)
            except TemporarilyBlockedError as exc:
                last_error = exc
                logger.warning("temporarily blocked, sleeping %.1fs (attempt %d)", exc.retry_after, attempt)
                await asyncio.sleep(exc.retry_after)
        raise last_error or RuntimeError("retries exhausted")
