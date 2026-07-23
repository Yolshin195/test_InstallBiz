from __future__ import annotations

from app.domain.entities import DigitStatistics, FileStatistics
from app.domain.ports.file_repository import FileRepository


class ComputeStatisticsUseCase:
    """Считает статистику встречаемости цифр по выбранным файлам.

    Возвращает и общую статистику по всем выбранным файлам, и разбивку
    по каждому файлу отдельно — как требует ТЗ.
    """

    def __init__(self, file_repository: FileRepository) -> None:
        self._file_repository = file_repository

    async def execute(self, file_names: list[str]) -> FileStatistics:
        if not file_names:
            return FileStatistics(total=DigitStatistics(), per_file={})

        files = await self._file_repository.get_by_names(file_names)

        total = DigitStatistics()
        per_file: dict[str, DigitStatistics] = {}
        for file in files:
            counts = file.digit_counts()
            file_stats = DigitStatistics(counts=counts)
            per_file[file.name] = file_stats
            total.add(counts)

        return FileStatistics(total=total, per_file=per_file)
