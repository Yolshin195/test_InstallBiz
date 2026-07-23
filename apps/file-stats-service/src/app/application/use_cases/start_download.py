from __future__ import annotations

import uuid

from app.domain.entities import DownloadProgress
from app.domain.ports.progress_store import ProgressStore
from app.domain.ports.task_dispatcher import DownloadTaskDispatcher


class StartDownloadUseCase:
    """Создаёт новую сессию скачивания и ставит фоновую задачу в очередь.

    Сама логика скачивания в этом use case НЕ выполняется — она лишь
    диспетчеризуется в Celery через порт DownloadTaskDispatcher. Реальную
    работу делает DownloadCatalogUseCase внутри воркера.
    """

    def __init__(self, task_dispatcher: DownloadTaskDispatcher, progress_store: ProgressStore) -> None:
        self._task_dispatcher = task_dispatcher
        self._progress_store = progress_store

    async def execute(self) -> str:
        session_id = str(uuid.uuid4())
        # Сразу публикуем идентификатор в состоянии "idle", чтобы SSE-клиент
        # мог подписаться ещё до того, как воркер реально возьмётся за задачу.
        await self._progress_store.set_progress(DownloadProgress(session_id=session_id))
        self._task_dispatcher.dispatch(session_id)
        return session_id
