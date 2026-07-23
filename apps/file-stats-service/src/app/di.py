from __future__ import annotations

from collections.abc import AsyncIterable

import httpx
from celery import Celery
from dishka import Provider, Scope, from_context, provide
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.adapters.outbound.celery.task_dispatcher import CeleryTaskDispatcher
from app.adapters.outbound.external_api.http_file_catalog_client import HttpFileCatalogClient
from app.adapters.outbound.persistence.repository import AlchemyFileRepository
from app.adapters.outbound.redis.progress_store import RedisProgressStore
from app.application.use_cases.compute_statistics import ComputeStatisticsUseCase
from app.application.use_cases.download_catalog import DownloadCatalogUseCase
from app.application.use_cases.get_progress import GetProgressUseCase
from app.application.use_cases.list_downloaded_files import ListDownloadedFilesUseCase
from app.application.use_cases.start_download import StartDownloadUseCase
from app.config import Settings
from app.domain.ports.file_catalog_client import FileCatalogClient
from app.domain.ports.file_repository import FileRepository
from app.domain.ports.progress_store import ProgressStore
from app.domain.ports.task_dispatcher import DownloadTaskDispatcher


class SettingsProvider(Provider):
    """Settings передаются из контекста при создании контейнера (см. main.py / tasks.py)."""

    settings = from_context(provides=Settings, scope=Scope.APP)


class InfrastructureProvider(Provider):
    """Низкоуровневые клиенты инфраструктуры: HTTP, Redis, БД, Celery."""

    scope = Scope.APP

    @provide
    async def httpx_client(self) -> AsyncIterable[httpx.AsyncClient]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            yield client

    @provide
    async def redis_client(self, settings: Settings) -> AsyncIterable[Redis]:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            yield redis
        finally:
            await redis.aclose()

    @provide
    def celery_app(self, settings: Settings) -> Celery:
        from app.celery_app import celery_app  # локальный импорт: избегаем цикла модулей

        return celery_app

    @provide
    def db_engine(self, settings: Settings) -> AsyncEngine:
        return create_async_engine(settings.postgres_dsn_async, pool_pre_ping=True)

    @provide
    def db_sessionmaker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(engine, expire_on_commit=False)


class RequestScopedProvider(Provider):
    """Всё, что должно жить в рамках одного HTTP-запроса или одного вызова celery-задачи."""

    scope = Scope.REQUEST

    @provide
    async def db_session(
        self, sessionmaker: async_sessionmaker[AsyncSession]
    ) -> AsyncIterable[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    file_repository = provide(AlchemyFileRepository, provides=FileRepository)
    progress_store = provide(RedisProgressStore, provides=ProgressStore)

    @provide
    def task_dispatcher(self, celery_app: Celery) -> DownloadTaskDispatcher:
        return CeleryTaskDispatcher(celery_app=celery_app)

    @provide
    def file_catalog_client(
        self, client: httpx.AsyncClient, settings: Settings
    ) -> FileCatalogClient:
        return HttpFileCatalogClient(
            client=client,
            base_url=settings.external_api_base_url,
            candidate_id=settings.external_api_candidate_id,
            requests_per_second=settings.external_api_rate_limit_per_second,
        )

    download_catalog_use_case = provide(DownloadCatalogUseCase)
    start_download_use_case = provide(StartDownloadUseCase)
    get_progress_use_case = provide(GetProgressUseCase)
    list_downloaded_files_use_case = provide(ListDownloadedFilesUseCase)
    compute_statistics_use_case = provide(ComputeStatisticsUseCase)


def get_providers() -> list[Provider]:
    return [SettingsProvider(), InfrastructureProvider(), RequestScopedProvider()]
