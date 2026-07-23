from __future__ import annotations

from pydantic import BaseModel


class StartDownloadResponse(BaseModel):
    session_id: str


class ProgressResponse(BaseModel):
    session_id: str
    status: str
    started_at: str | None
    finished_at: str | None
    total_known: int
    downloaded: int
    message: str | None


class ComputeStatsRequest(BaseModel):
    file_names: list[str]
