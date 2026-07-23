from typing import Protocol

from app.domain.entities import DownloadedFile


class FileRepository(Protocol):
    """Порт для хранения скачанных файлов (реализация — Postgres/Advanced Alchemy)."""

    async def save_many(self, files: list[DownloadedFile]) -> None:
        """Сохранить (upsert по имени) пачку скачанных файлов."""
        ...

    async def existing_names(self, names: list[str]) -> set[str]:
        """Из списка имён вернуть те, что уже сохранены у нас."""
        ...

    async def list_paginated(
        self, page: int, page_size: int
    ) -> tuple[list[DownloadedFile], int]:
        """Список файлов, отсортированный по времени скачивания, с пагинацией.

        Возвращает (страница_файлов, всего_файлов).
        """
        ...

    async def get_by_names(self, names: list[str]) -> list[DownloadedFile]:
        """Получить файлы с содержимым по списку имён (для расчёта статистики)."""
        ...

    async def all_names(self) -> list[str]:
        """Все имена скачанных файлов (для варианта 'выбрать вообще все')."""
        ...

    async def count(self) -> int:
        ...
