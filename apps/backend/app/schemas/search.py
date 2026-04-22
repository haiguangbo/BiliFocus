from pydantic import BaseModel, Field

from app.schemas.video import VideoItem


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    filter_text: str | None = None
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0)
    source: str = "default"


class SearchSyncRequest(BaseModel):
    query: str = Field(min_length=1)
    filter_text: str | None = None
    limit: int = Field(default=20, ge=1, le=50)
    source: str = "default"


class SearchResponse(BaseModel):
    query: str
    filter_text: str | None = None
    items: list[VideoItem]
    total: int
    limit: int
    offset: int


class SearchSyncResponse(BaseModel):
    job_id: str
    status: str
    query: str
    saved_count: int
    skipped_count: int
    failed_count: int
    started_at: str
    finished_at: str
