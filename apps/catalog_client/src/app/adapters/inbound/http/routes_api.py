from __future__ import annotations

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException

from app.adapters.inbound.http.schemas import ProgressResponse
from app.application.use_cases.get_progress import GetProgressUseCase

router = APIRouter(prefix="/api", route_class=DishkaRoute)


@router.get("/progress/{session_id}", response_model=ProgressResponse)
async def get_progress_snapshot(
    session_id: str, get_progress: FromDishka[GetProgressUseCase]
) -> ProgressResponse:
    progress = await get_progress.current(session_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Сессия скачивания не найдена")
    return ProgressResponse(**progress.to_dict())
