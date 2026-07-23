from celery import Celery


class CeleryTaskDispatcher:
    """Реализация порта DownloadTaskDispatcher: ставит задачу в очередь Celery.

    Никакой бизнес-логики здесь нет — только .delay(...). Сама логика
    выполняется в DownloadCatalogUseCase, который celery-задача вызывает
    внутри воркера (см. adapters/inbound/celery_tasks/tasks.py).
    """

    def __init__(self, celery_app: Celery, task_name: str = "download_catalog") -> None:
        self._celery_app = celery_app
        self._task_name = task_name

    def dispatch(self, session_id: str) -> None:
        self._celery_app.send_task(self._task_name, args=[session_id])
