from __future__ import annotations

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.persistence.models import FileModel
from app.domain.entities import DownloadedFile


class _FileModelRepository(SQLAlchemyAsyncRepository[FileModel]):
    """Технический репозиторий Advanced Alchemy для FileModel."""

    model_type = FileModel


class AlchemyFileRepository:
    """Реализация порта FileRepository поверх Advanced Alchemy / SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = _FileModelRepository(session=session, auto_commit=True)

    @staticmethod
    def _to_entity(model: FileModel) -> DownloadedFile:
        return DownloadedFile(
            id=model.id,
            name=model.name,
            content=model.content,
            downloaded_at=model.downloaded_at,
        )

    async def save_many(self, files: list[DownloadedFile]) -> None:
        if not files:
            return
        # Upsert по имени файла: идемпотентно на случай повторного запуска задачи.
        stmt = pg_insert(FileModel).values(
            [
                {
                    "name": f.name,
                    "content": f.content,
                    "downloaded_at": f.downloaded_at,
                }
                for f in files
            ]
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[FileModel.name],
            set_={
                "content": stmt.excluded.content,
                "downloaded_at": stmt.excluded.downloaded_at,
            },
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def existing_names(self, names: list[str]) -> set[str]:
        if not names:
            return set()
        result = await self._session.execute(
            select(FileModel.name).where(FileModel.name.in_(names))
        )
        return set(result.scalars().all())

    async def list_paginated(self, page: int, page_size: int) -> tuple[list[DownloadedFile], int]:
        offset = (page - 1) * page_size
        result = await self._session.execute(
            select(FileModel)
            .order_by(FileModel.downloaded_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = [self._to_entity(m) for m in result.scalars().all()]
        total = await self.count()
        return items, total

    async def get_by_names(self, names: list[str]) -> list[DownloadedFile]:
        if not names:
            return []
        result = await self._session.execute(select(FileModel).where(FileModel.name.in_(names)))
        return [self._to_entity(m) for m in result.scalars().all()]

    async def all_names(self) -> list[str]:
        result = await self._session.execute(select(FileModel.name))
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(FileModel))
        return int(result.scalar_one())
