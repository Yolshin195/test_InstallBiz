from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from redis.asyncio import Redis

from app.domain.entities import DownloadProgress

logger = logging.getLogger(__name__)

_KEY_PREFIX = "download:progress:"
_CHANNEL_PREFIX = "download:progress:channel:"
_TTL_SECONDS = 60 * 60 * 6  # 6 часов достаточно, чтобы UI успел прочитать финальный статус


class RedisProgressStore:
    """Реализация порта ProgressStore поверх Redis.

    Хранение: JSON по ключу `download:progress:{session_id}` (источник истины,
    его же читает GET /api/progress/{session_id} и первичный SSE-снимок).
    Уведомления: pub/sub канал `download:progress:channel:{session_id}` —
    на него подписывается SSE-эндпоинт, чтобы не поллить Redis в цикле.
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @staticmethod
    def _key(session_id: str) -> str:
        return f"{_KEY_PREFIX}{session_id}"

    @staticmethod
    def _channel(session_id: str) -> str:
        return f"{_CHANNEL_PREFIX}{session_id}"

    async def set_progress(self, progress: DownloadProgress) -> None:
        payload = json.dumps(progress.to_dict())
        await self._redis.set(self._key(progress.session_id), payload, ex=_TTL_SECONDS)
        await self._redis.publish(self._channel(progress.session_id), payload)

    async def get_progress(self, session_id: str) -> DownloadProgress | None:
        raw = await self._redis.get(self._key(session_id))
        if raw is None:
            return None
        return DownloadProgress.from_dict(json.loads(raw))

    async def subscribe(self, session_id: str) -> AsyncIterator[DownloadProgress]:
        # Сначала отдаём текущее состояние (клиент мог подписаться уже после старта).
        current = await self.get_progress(session_id)
        if current is not None:
            yield current
            if current.status in ("completed", "error"):
                return

        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self._channel(session_id))
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
                if message is None:
                    # keep-alive: на случай пропущенного pub/sub-сообщения перечитываем ключ
                    progress = await self.get_progress(session_id) or current
                else:
                    progress = DownloadProgress.from_dict(json.loads(message["data"]))
                yield progress
                if progress.status in ("completed", "error"):
                    break
        finally:
            await pubsub.unsubscribe(self._channel(session_id))
            await pubsub.close()
