from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


DIGITS = tuple("0123456789")


@dataclass(slots=True)
class DownloadedFile:
    """Файл, скачанный из внешнего каталога и сохранённый у нас."""

    name: str
    content: str
    downloaded_at: datetime
    id: uuid.UUID | None = None

    def digit_counts(self) -> dict[str, int]:
        counts = dict.fromkeys(DIGITS, 0)
        for ch in self.content:
            if ch in counts:
                counts[ch] += 1
        return counts


class DownloadStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass(slots=True)
class DownloadProgress:
    """Прогресс фоновой задачи скачивания каталога. Хранится в Redis."""

    session_id: str
    status: DownloadStatus = DownloadStatus.IDLE
    started_at: datetime | None = None
    finished_at: datetime | None = None
    total_known: int = 0  # сколько имён файлов получено суммарно (может расти по ходу)
    downloaded: int = 0  # сколько файлов реально скачано и сохранено
    message: str | None = None

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "total_known": self.total_known,
            "downloaded": self.downloaded,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DownloadProgress:
        return cls(
            session_id=data["session_id"],
            status=DownloadStatus(data["status"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            finished_at=datetime.fromisoformat(data["finished_at"]) if data.get("finished_at") else None,
            total_known=data.get("total_known", 0),
            downloaded=data.get("downloaded", 0),
            message=data.get("message"),
        )


@dataclass(slots=True)
class DigitStatistics:
    """Статистика встречаемости цифр 0-9."""

    counts: dict[str, int] = field(default_factory=lambda: dict.fromkeys(DIGITS, 0))

    def add(self, other: dict[str, int]) -> None:
        for digit, count in other.items():
            self.counts[digit] = self.counts.get(digit, 0) + count


@dataclass(slots=True)
class FileStatistics:
    """Результат расчёта: общая статистика + разбивка по файлам."""

    total: DigitStatistics
    per_file: dict[str, DigitStatistics]
