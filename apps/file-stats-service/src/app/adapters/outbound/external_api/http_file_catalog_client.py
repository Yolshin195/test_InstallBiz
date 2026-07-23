from __future__ import annotations

import io
import logging
import zipfile

import httpx
from pyrate_limiter import Duration, Limiter, Rate

from app.domain.exceptions import (
    FilesNotFoundError,
    RateLimitedError,
    TemporarilyBlockedError,
)

logger = logging.getLogger(__name__)


class HttpFileCatalogClient:
    """Адаптер порта FileCatalogClient поверх httpx.

    Самоограничение частоты запросов реализовано через pyrate-limiter
    (проактивно не долбим API быстрее заданного лимита), а 429/403,
    которые всё же может вернуть сервер, транслируются в доменные
    исключения с retry_after, извлечённым из заголовка Retry-After —
    их уже обрабатывает use case (DownloadCatalogUseCase).
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        candidate_id: str | None,
        requests_per_second: float,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._candidate_id = candidate_id
        # Например requests_per_second=2 -> не более 2 запросов за 1000 мс.
        rate = Rate(max(int(requests_per_second * 10), 1), Duration.SECOND * 10)
        self._limiter = Limiter(rate)

    def _headers(self) -> dict[str, str]:
        headers = {}
        if self._candidate_id:
            headers["X-Candidate-Id"] = self._candidate_id
        return headers

    async def _throttle(self) -> None:
        # pyrate-limiter в синхронном режиме — вызов дешёвый, не блокирует event loop надолго.
        while not self._limiter.try_acquire("external-api"):
            await self._async_sleep_backoff()

    @staticmethod
    async def _async_sleep_backoff() -> None:
        import asyncio

        await asyncio.sleep(0.05)

    @staticmethod
    def _retry_after_seconds(response: httpx.Response, default: float = 5.0) -> float:
        header = response.headers.get("Retry-After")
        if header is None:
            return default
        try:
            return float(header)
        except ValueError:
            return default

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code == 429:
            raise RateLimitedError(self._retry_after_seconds(response), response.text)
        if response.status_code == 403:
            raise TemporarilyBlockedError(self._retry_after_seconds(response, default=1800.0), response.text)
        if response.status_code == 404:
            raise FilesNotFoundError(response.text)
        response.raise_for_status()

    async def get_names(self) -> list[str]:
        await self._throttle()
        response = await self._client.get(
            f"{self._base_url}/api/files/names", headers=self._headers()
        )
        self._raise_for_status(response)
        data = response.json()
        return data["file_names"]

    async def download(self, names: list[str]) -> dict[str, str]:
        await self._throttle()
        response = await self._client.post(
            f"{self._base_url}/api/files/download",
            headers=self._headers(),
            json={"file_names": names},
        )
        self._raise_for_status(response)

        content_map: dict[str, str] = {}
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = info.filename.split("/")[-1]
                content_map[name] = archive.read(info).decode("utf-8").strip()
        return content_map

    async def mark_downloaded(self, names: list[str]) -> None:
        await self._throttle()
        response = await self._client.post(
            f"{self._base_url}/api/files/downloaded",
            headers=self._headers(),
            json={"file_names": names},
        )
        self._raise_for_status(response)
