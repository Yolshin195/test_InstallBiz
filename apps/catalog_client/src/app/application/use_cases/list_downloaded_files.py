from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities import DownloadedFile
from app.domain.ports.file_repository import FileRepository


@dataclass(slots=True)
class FilesPage:
    items: list[DownloadedFile]
    page: int
    page_size: int
    total: int

    @property
    def total_pages(self) -> int:
        if self.total == 0:
            return 1
        return (self.total + self.page_size - 1) // self.page_size


class ListDownloadedFilesUseCase:
    """Список скачанных файлов, отсортированный по времени скачивания, с пагинацией."""

    def __init__(self, file_repository: FileRepository) -> None:
        self._file_repository = file_repository

    async def execute(self, page: int = 1, page_size: int = 20) -> FilesPage:
        page = max(page, 1)
        page_size = max(min(page_size, 200), 1)
        items, total = await self._file_repository.list_paginated(page, page_size)
        return FilesPage(items=items, page=page, page_size=page_size, total=total)

    async def all_names(self) -> list[str]:
        """Для выбора 'вообще все файлы' — без пагинации."""
        return await self._file_repository.all_names()
