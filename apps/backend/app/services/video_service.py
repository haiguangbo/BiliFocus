from collections.abc import Iterable
from datetime import UTC, datetime

from app.providers.base import ProviderUnavailableError
from app.providers.factory import SearchProviderFactory
from app.repositories.video_repository import VideoRepository
from app.schemas.search import SearchSyncResponse
from app.schemas.video import (
    PlaybackSource,
    VideoCacheResponse,
    VideoDeleteResponse,
    VideoDetail,
    VideoListResponse,
    VideoPlaybackProgressResponse,
)
from app.services.download_service import DownloadService


class VideoService:
    def __init__(
        self,
        repository: VideoRepository,
        provider_factory: SearchProviderFactory,
        download_service: DownloadService | None = None,
    ) -> None:
        self.repository = repository
        self.provider_factory = provider_factory
        self.download_service = download_service

    def list_videos(
        self,
        *,
        q: str | None,
        tag: str | None,
        sort: str,
        limit: int,
        offset: int,
    ) -> VideoListResponse:
        items, total = self.repository.list_videos(q=q, tag=tag, sort=sort, limit=limit, offset=offset)
        return VideoListResponse(items=items, total=total, limit=limit, offset=offset)

    def get_video(self, bvid: str) -> VideoDetail | None:
        cached = self.repository.get_by_bvid(bvid)
        if cached is not None:
            return cached

        provider = self.provider_factory.resolve("default")
        detail = provider.get_video(bvid)
        if detail is None:
            return None

        preview_extra = dict(detail.raw_extra)
        preview_extra["preview_only"] = "true"
        return detail.model_copy(
            update={
                "cached": False,
                "sync_status": "preview",
                "raw_extra": preview_extra,
            }
        )

    def sync_video(self, bvid: str) -> SearchSyncResponse:
        started_at = datetime.now(UTC)
        provider = self.provider_factory.resolve("default")
        detail = provider.get_video(bvid)
        if detail is None:
            raise ProviderUnavailableError("video detail unavailable")
        saved_count, skipped_count = self.repository.upsert_many([detail])
        self.repository.db.commit()
        finished_at = datetime.now(UTC)
        return SearchSyncResponse(
            job_id=f"sync_video_{started_at.strftime('%Y%m%d_%H%M%S')}",
            status="completed",
            query=bvid,
            saved_count=saved_count,
            skipped_count=skipped_count,
            failed_count=0,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
        )

    def sync_series(self, bvid: str, *, limit: int = 20) -> SearchSyncResponse:
        started_at = datetime.now(UTC)
        provider = self.provider_factory.resolve("default")
        detail = self.get_video(bvid)
        if detail is None:
            raise ProviderUnavailableError("video detail unavailable")

        series_query = detail.series_title or self._fallback_series_query(detail.title)
        candidates = provider.search(series_query)
        normalized_target = self._normalize_series_key(series_query)
        accepted = [
            item
            for item in candidates
            if self._normalize_series_key(item.series_title or item.title).startswith(normalized_target)
            or normalized_target.startswith(self._normalize_series_key(item.series_title or item.title))
        ]
        if not accepted:
            accepted = candidates

        saved_count, skipped_count = self.repository.upsert_many(accepted[:limit])
        self.repository.db.commit()
        finished_at = datetime.now(UTC)
        return SearchSyncResponse(
            job_id=f"sync_series_{started_at.strftime('%Y%m%d_%H%M%S')}",
            status="completed",
            query=series_query,
            saved_count=saved_count,
            skipped_count=skipped_count,
            failed_count=0,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
        )

    def cache_video(self, bvid: str, quality_code: str | None = None) -> VideoCacheResponse:
        if self.download_service is None:
            raise ProviderUnavailableError("download service unavailable")
        return self.download_service.cache_video(bvid=bvid, quality_code=quality_code)

    def get_playback(
        self,
        bvid: str,
        quality_code: str | None = None,
        cid: str | None = None,
    ) -> PlaybackSource | None:
        provider = self.provider_factory.resolve("default")
        return provider.get_playback_source(bvid, quality_code=quality_code, cid=cid)

    def stream_video(
        self,
        bvid: str,
        *,
        quality_code: str | None = None,
        cid: str | None = None,
        range_header: str | None = None,
    ) -> tuple[Iterable[bytes], int, dict[str, str]] | None:
        provider = self.provider_factory.resolve("default")
        source = provider.get_playback_source(bvid, quality_code=quality_code, cid=cid)
        if source is None:
            return None
        return provider.stream_playback_source(source, range_header=range_header)

    def record_playback_progress(
        self,
        *,
        bvid: str,
        position_seconds: float,
        duration_seconds: float | None,
        completed: bool,
    ) -> VideoPlaybackProgressResponse:
        last_played_at = datetime.now(UTC).isoformat()
        progress_percent = 0.0
        if duration_seconds and duration_seconds > 0:
            progress_percent = round(min(position_seconds / duration_seconds, 1.0) * 100, 2)

        existing = self.repository.get_by_bvid(bvid)
        current_raw_extra = existing.raw_extra if existing is not None else {}
        session_count = int(current_raw_extra.get("playback_session_count", "0") or "0")
        previous_position = float(current_raw_extra.get("playback_position_seconds", "0") or "0")
        if completed or (position_seconds <= 5 and previous_position <= 5):
            session_count += 1

        self.repository.update_raw_extra(
            bvid,
            {
                "playback_position_seconds": f"{position_seconds:.2f}",
                "playback_duration_seconds": f"{duration_seconds:.2f}" if duration_seconds is not None else "",
                "playback_progress_percent": f"{progress_percent:.2f}",
                "playback_last_played_at": last_played_at,
                "playback_completed": "true" if completed else "false",
                "playback_session_count": str(session_count),
            },
        )
        self.repository.db.commit()
        return VideoPlaybackProgressResponse(
            bvid=bvid,
            status="completed",
            position_seconds=round(position_seconds, 2),
            duration_seconds=round(duration_seconds, 2) if duration_seconds is not None else None,
            progress_percent=progress_percent,
            completed=completed,
            last_played_at=last_played_at,
        )

    def delete_video(self, bvid: str) -> VideoDeleteResponse | None:
        deleted = self.repository.delete_by_bvid(bvid)
        if not deleted:
            return None
        self.repository.db.commit()
        return VideoDeleteResponse(bvid=bvid, status="deleted")

    def _fallback_series_query(self, title: str) -> str:
        normalized = title
        for token in ["【", "】", "(", ")", "（", "）"]:
            normalized = normalized.replace(token, " ")
        for pattern in [r"第\s*\d+\s*[季集话]", r"(?:ep|episode|e)\s*\d+", r"\d+\s*集", r"\d+\s*连播"]:
            import re

            normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)
        return " ".join(normalized.split()).strip() or title

    def _normalize_series_key(self, value: str) -> str:
        import re

        return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value.lower())
