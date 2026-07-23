from typing import Protocol


class FileCatalogClient(Protocol):
    """Порт для общения с внешним API каталога файлов.

    Реализация (адаптер) отвечает за HTTP, самоограничение частоты запросов
    и разбор ответов 429/403 в доменные исключения RateLimitedError /
    TemporarilyBlockedError — сценарий использования лишь ловит эти
    исключения и решает, сколько ждать перед повтором.
    """

    async def get_names(self) -> list[str]:
        """Вернуть очередную порцию (3-9) ещё не скачанных имён файлов.

        Пустой список означает, что каталог скачан полностью.
        """
        ...

    async def download(self, names: list[str]) -> dict[str, str]:
        """Скачать содержимое файлов (не более 3 за раз) и вернуть {имя: содержимое}."""
        ...

    async def mark_downloaded(self, names: list[str]) -> None:
        """Отметить файлы как скачанные, чтобы они не попадали в get_names."""
        ...
