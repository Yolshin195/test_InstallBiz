from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class FileModel(UUIDAuditBase):
    """Таблица скачанных файлов.

    Наследуется от UUIDAuditBase (Advanced Alchemy) — получаем id: UUID
    и created_at/updated_at "из коробки".
    """

    __tablename__ = "downloaded_files"
    __table_args__ = (UniqueConstraint("name", name="uq_downloaded_files_name"),)

    name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    downloaded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
