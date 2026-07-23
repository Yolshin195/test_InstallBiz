class FileCatalogError(Exception):
    """Базовая ошибка при работе с внешним каталогом файлов."""


class RateLimitedError(FileCatalogError):
    """Внешнее API вернуло 429 — нужно подождать retry_after секунд и повторить."""

    def __init__(self, retry_after: float, detail: str = "") -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limited, retry after {retry_after}s: {detail}")


class TemporarilyBlockedError(FileCatalogError):
    """Внешнее API вернуло 403 — клиент забанен на retry_after секунд."""

    def __init__(self, retry_after: float, detail: str = "") -> None:
        self.retry_after = retry_after
        super().__init__(f"Blocked, retry after {retry_after}s: {detail}")


class FilesNotFoundError(FileCatalogError):
    """Часть запрошенных файлов отсутствует в каталоге (404)."""
