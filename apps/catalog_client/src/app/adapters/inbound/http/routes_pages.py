from __future__ import annotations

import asyncio
import logging
from zoneinfo import ZoneInfo

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.application.use_cases.compute_statistics import ComputeStatisticsUseCase
from app.application.use_cases.get_progress import GetProgressUseCase
from app.application.use_cases.list_downloaded_files import ListDownloadedFilesUseCase
from app.application.use_cases.start_download import StartDownloadUseCase
from app.config import Settings

logger = logging.getLogger(__name__)

router = APIRouter(route_class=DishkaRoute)
templates = Jinja2Templates(directory="src/app/templates")


@router.get("/", include_in_schema=False)
async def index() -> RedirectResponse:
    return RedirectResponse(url="/download")


@router.get("/download", response_class=HTMLResponse)
async def download_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "download.html", {})


@router.post("/download/start", response_class=HTMLResponse)
async def download_start(
    request: Request,
    start_download: FromDishka[StartDownloadUseCase],
    settings: FromDishka[Settings],
) -> HTMLResponse:
    session_id = await start_download.execute()
    started_local = _now_local(settings)
    return templates.TemplateResponse(
        request,
        "partials/progress_container.html",
        {"session_id": session_id, "started_local": started_local},
    )


@router.get("/download/progress/stream/{session_id}")
async def download_progress_stream(
    request: Request,
    session_id: str,
    get_progress: FromDishka[GetProgressUseCase],
    settings: FromDishka[Settings],
) -> StreamingResponse:
    """SSE-эндпоинт: транслирует обновления прогресса из Redis в виде HTML-фрагментов
    (совместимо с htmx SSE extension, sse-swap="message")."""

    async def event_generator():
        try:
            async for progress in get_progress.stream(session_id):
                if await request.is_disconnected():
                    break
                html = templates.get_template("partials/progress_fragment.html").render(
                    {
                        "progress": progress,
                        "started_local": _fmt_local(progress.started_at, settings),
                        "finished_local": _fmt_local(progress.finished_at, settings),
                    }
                )
                yield _format_sse(html)
                if progress.status in ("completed", "error"):
                    break
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _format_sse(html: str, event: str = "message") -> str:
    data_lines = "\n".join(f"data: {line}" for line in html.splitlines() or [""])
    return f"event: {event}\n{data_lines}\n\n"


def _now_local(settings: Settings) -> str:
    from datetime import datetime, timezone

    return _fmt_local(datetime.now(tz=timezone.utc), settings)


def _fmt_local(value, settings: Settings) -> str | None:
    if value is None:
        return None
    local = value.astimezone(ZoneInfo(settings.display_tz))
    return local.strftime("%Y-%m-%d %H:%M:%S %Z")


@router.get("/files", response_class=HTMLResponse)
async def files_page(
    request: Request,
    list_files: FromDishka[ListDownloadedFilesUseCase],
    page: int = 1,
) -> HTMLResponse:
    files_page_data = await list_files.execute(page=page, page_size=20)
    return templates.TemplateResponse(
        request, "files.html", {"files_page": files_page_data}
    )


@router.get("/files/table", response_class=HTMLResponse)
async def files_table_partial(
    request: Request,
    list_files: FromDishka[ListDownloadedFilesUseCase],
    page: int = 1,
) -> HTMLResponse:
    files_page_data = await list_files.execute(page=page, page_size=20)
    return templates.TemplateResponse(
        request, "partials/files_table.html", {"files_page": files_page_data}
    )


@router.post("/files/compute-stats", response_class=HTMLResponse)
async def compute_stats(
    request: Request,
    compute_statistics: FromDishka[ComputeStatisticsUseCase],
    list_files: FromDishka[ListDownloadedFilesUseCase],
    file_names: list[str] = Form(default_factory=list),
    select_all: str | None = Form(default=None),
) -> HTMLResponse:
    if select_all == "true":
        file_names = await list_files.all_names()

    stats = await compute_statistics.execute(file_names)
    return templates.TemplateResponse(
        request,
        "partials/stats.html",
        {"stats": stats, "selected_count": len(file_names)},
    )
