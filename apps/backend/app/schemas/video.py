from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RecommendationReason(BaseModel):
    code: str
    message: str


class VideoItem(BaseModel):
    bvid: str
    title: str
    author_name: str
    cover_url: str | None = None
    duration_seconds: int | None = None
    published_at: datetime | None = None
    view_count: int | None = None
    like_count: int | None = None
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    primary_category: str | None = None
    secondary_category: str | None = None
    series_key: str | None = None
    series_title: str | None = None
    playback_position_seconds: float | None = None
    playback_progress_percent: float | None = None
    playback_last_played_at: datetime | None = None
    playback_completed: bool = False
    match_reasons: list[RecommendationReason] = Field(default_factory=list)
    cached: bool


class VideoDetail(VideoItem):
    description: str | None = None
    source_url: str | None = None
    sync_status: str = "synced"
    last_synced_at: datetime | None = None
    raw_extra: dict[str, str] = Field(default_factory=dict)


class PlaybackQualityOption(BaseModel):
    code: str
    label: str


class PlaybackSegment(BaseModel):
    url: str
    size: int | None = None


class PlaybackSource(BaseModel):
    bvid: str
    cid: str
    selected_quality_code: str
    selected_quality_label: str
    source_url: str
    segments: list[PlaybackSegment] = Field(default_factory=list)
    total_size: int | None = None
    qualities: list[PlaybackQualityOption] = Field(default_factory=list)


class VideoPlaybackResponse(BaseModel):
    bvid: str
    cid: str
    selected_quality_code: str
    selected_quality_label: str
    stream_url: str
    qualities: list[PlaybackQualityOption] = Field(default_factory=list)


class VideoCacheResponse(BaseModel):
    bvid: str
    status: str
    output_path: str
    quality_code: str
    quality_label: str
    bytes_written: int


class VideoMetadataRewriteRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    tag: str | None = None


class VideoMetadataRewriteResponse(BaseModel):
    job_id: str
    status: str
    rewritten_count: int
    skipped_count: int
    updated_bvids: list[str] = Field(default_factory=list)
    started_at: str
    finished_at: str


class VideoPlaybackProgressRequest(BaseModel):
    position_seconds: float = Field(ge=0)
    duration_seconds: float | None = Field(default=None, ge=0)
    completed: bool = False


class VideoPlaybackProgressResponse(BaseModel):
    bvid: str
    status: str
    position_seconds: float
    duration_seconds: float | None = None
    progress_percent: float
    completed: bool
    last_played_at: str


class VideoDeleteResponse(BaseModel):
    bvid: str
    status: str


class VideoListResponse(BaseModel):
    items: list[VideoItem]
    total: int
    limit: int
    offset: int
