from typing import Protocol


class DownloadTaskDispatcher(Protocol):
    """Порт для запуска фоновой задачи скачивания.

    Единственная реализация — Celery-адаптер (.delay(...)), но application-слой
    про Celery ничего не знает: он просит "запусти фоновую задачу для этой сессии".
    """

    def dispatch(self, session_id: str) -> None: ...
