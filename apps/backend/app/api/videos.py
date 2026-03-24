import re
from urllib.parse import quote
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.providers.base import ProviderUnavailableError
from app.providers.factory import SearchProviderFactory
from app.repositories.preference_repository import PreferenceRepository
from app.repositories.video_repository import VideoRepository
from app.schemas.search import SearchSyncResponse
from app.schemas.video import (
    VideoCacheResponse,
    VideoDeleteResponse,
    VideoDetail,
    VideoListResponse,
    VideoMetadataRewriteRequest,
    VideoMetadataRewriteResponse,
    VideoPlaybackProgressRequest,
    VideoPlaybackProgressResponse,
    VideoPlaybackResponse,
)
from app.services.download_service import DownloadService
from app.services.metadata_rewrite_service import MetadataRewriteService
from app.services.video_service import VideoService

router = APIRouter(tags=["videos"])


def build_download_filename(title: str, quality: str | None = None) -> str:
    compact = re.sub(r"\s+", " ", title).strip()
    safe_title = re.sub(r'[\\/:*?"<>|]+', "_", compact)[:120] or "video"
    suffix = f"-{quality}" if quality else ""
    return f"{safe_title}{suffix}.mp4"


def get_video_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> VideoService:
    repository = VideoRepository(db)
    preferences = PreferenceRepository(db).get_or_create()
    provider_factory = SearchProviderFactory(settings, bilibili_cookie=preferences.bilibili_cookie)
    download_service = DownloadService(
        repository=repository,
        provider_factory=provider_factory,
        download_output_dir=preferences.download_output_dir,
    )
    return VideoService(repository=repository, provider_factory=provider_factory, download_service=download_service)


def get_metadata_rewrite_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MetadataRewriteService:
    repository = VideoRepository(db)
    return MetadataRewriteService(
        settings=settings,
        repository=repository,
    )


@router.get("/videos", response_model=VideoListResponse)
def list_videos(
    q: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: Literal["recent", "views", "published_at"] = Query(default="recent"),
    service: VideoService = Depends(get_video_service),
) -> VideoListResponse:
    return service.list_videos(q=q, tag=tag, sort=sort, limit=limit, offset=offset)


@router.get("/videos/{bvid}", response_model=VideoDetail)
def get_video_detail(
    bvid: str,
    service: VideoService = Depends(get_video_service),
) -> VideoDetail:
    try:
        item = service.get_video(bvid)
    except ProviderUnavailableError:
        raise HTTPException(status_code=503, detail="provider unavailable")
    if item is None:
        raise HTTPException(status_code=404, detail="video not found")
    return item


@router.delete("/videos/{bvid}", response_model=VideoDeleteResponse)
def delete_video(
    bvid: str,
    service: VideoService = Depends(get_video_service),
) -> VideoDeleteResponse:
    item = service.delete_video(bvid)
    if item is None:
        raise HTTPException(status_code=404, detail="video not found")
    return item


@router.post("/videos/{bvid}/sync", response_model=SearchSyncResponse)
def sync_single_video(
    bvid: str,
    service: VideoService = Depends(get_video_service),
) -> SearchSyncResponse:
    try:
        return service.sync_video(bvid)
    except ProviderUnavailableError:
        raise HTTPException(status_code=503, detail="provider unavailable")


@router.post("/videos/{bvid}/sync-series", response_model=SearchSyncResponse)
def sync_video_series(
    bvid: str,
    limit: int = Query(default=20, ge=1, le=50),
    service: VideoService = Depends(get_video_service),
) -> SearchSyncResponse:
    try:
        return service.sync_series(bvid, limit=limit)
    except ProviderUnavailableError:
        raise HTTPException(status_code=503, detail="provider unavailable")


@router.post("/videos/{bvid}/cache", response_model=VideoCacheResponse)
def cache_single_video(
    bvid: str,
    quality: str | None = Query(default=None),
    service: VideoService = Depends(get_video_service),
) -> VideoCacheResponse:
    try:
        return service.cache_video(bvid, quality_code=quality)
    except ProviderUnavailableError:
        raise HTTPException(status_code=503, detail="provider unavailable")


@router.post("/videos/rewrite-metadata", response_model=VideoMetadataRewriteResponse)
def rewrite_library_metadata(
    payload: VideoMetadataRewriteRequest,
    service: MetadataRewriteService = Depends(get_metadata_rewrite_service),
) -> VideoMetadataRewriteResponse:
    return service.rewrite_library_metadata(limit=payload.limit, tag=payload.tag)


@router.get("/videos/{bvid}/playback", response_model=VideoPlaybackResponse)
def get_video_playback(
    bvid: str,
    request: Request,
    quality: str | None = Query(default=None),
    cid: str | None = Query(default=None),
    service: VideoService = Depends(get_video_service),
) -> VideoPlaybackResponse:
    try:
        source = service.get_playback(bvid, quality_code=quality, cid=cid)
    except ProviderUnavailableError:
        raise HTTPException(status_code=503, detail="provider unavailable")
    if source is None:
        raise HTTPException(status_code=404, detail="playback not available")

    stream_url = str(request.url_for("stream_video", bvid=bvid))
    stream_params: list[str] = []
    if source.selected_quality_code:
        stream_params.append(f"quality={source.selected_quality_code}")
    if source.cid:
        stream_params.append(f"cid={source.cid}")
    if stream_params:
        stream_url = f"{stream_url}?{'&'.join(stream_params)}"

    return VideoPlaybackResponse(
        bvid=source.bvid,
        cid=source.cid,
        selected_quality_code=source.selected_quality_code,
        selected_quality_label=source.selected_quality_label,
        stream_url=stream_url,
        qualities=source.qualities,
    )


@router.post("/videos/{bvid}/playback-progress", response_model=VideoPlaybackProgressResponse)
def record_playback_progress(
    bvid: str,
    payload: VideoPlaybackProgressRequest,
    service: VideoService = Depends(get_video_service),
) -> VideoPlaybackProgressResponse:
    return service.record_playback_progress(
        bvid=bvid,
        position_seconds=payload.position_seconds,
        duration_seconds=payload.duration_seconds,
        completed=payload.completed,
    )


@router.get("/videos/{bvid}/stream", name="stream_video")
def stream_video(
    bvid: str,
    request: Request,
    quality: str | None = Query(default=None),
    cid: str | None = Query(default=None),
    service: VideoService = Depends(get_video_service),
) -> StreamingResponse:
    try:
        payload = service.stream_video(
            bvid,
            quality_code=quality,
            cid=cid,
            range_header=request.headers.get("range"),
        )
    except ProviderUnavailableError:
        raise HTTPException(status_code=503, detail="provider unavailable")
    if payload is None:
        raise HTTPException(status_code=404, detail="playback not available")

    iterator, status_code, upstream_headers = payload
    normalized_headers = {key.lower(): value for key, value in upstream_headers.items()}
    media_type = normalized_headers.get("content-type", "video/mp4")
    response_headers: dict[str, str] = {"Cache-Control": "no-store"}
    try:
        detail = service.get_video(bvid)
    except ProviderUnavailableError:
        detail = None
    if "content-length" in normalized_headers:
        response_headers["Content-Length"] = normalized_headers["content-length"]
    if "content-range" in normalized_headers:
        response_headers["Content-Range"] = normalized_headers["content-range"]
    if "accept-ranges" in normalized_headers:
        response_headers["Accept-Ranges"] = normalized_headers["accept-ranges"]
    filename = build_download_filename(
        detail.title if detail else bvid,
        quality,
    )
    response_headers["Content-Disposition"] = f"inline; filename*=UTF-8''{quote(filename)}"

    return StreamingResponse(
        iterator,
        status_code=status_code,
        media_type=media_type,
        headers=response_headers,
    )
