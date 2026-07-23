from __future__ import annotations

import logging

from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.adapters.inbound.http.routes_api import router as api_router
from app.adapters.inbound.http.routes_pages import router as pages_router
from app.config import Settings, get_settings
from app.di import get_providers
from app.logging_config import configure_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(title="File Stats Service")
    app.include_router(pages_router)
    app.include_router(api_router)
    app.mount("/static", StaticFiles(directory="src/app/static"), name="static")

    container = make_async_container(*get_providers(), context={Settings: settings})
    setup_dishka(container, app)

    logger.info("application configured, external API base url=%s", settings.external_api_base_url)
    return app
