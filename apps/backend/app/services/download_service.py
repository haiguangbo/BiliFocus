from __future__ import annotations

import re
from pathlib import Path

from app.core.config import PROJECT_ROOT
from app.providers.base import ProviderUnavailableError
from app.providers.factory import SearchProviderFactory
from app.repositories.video_repository import VideoRepository
from app.schemas.video import VideoCacheResponse


class DownloadService:
    def __init__(
        self,
        *,
        repository: VideoRepository,
        provider_factory: SearchProviderFactory,
        download_output_dir: str,
    ) -> None:
        self.repository = repository
        self.provider_factory = provider_factory
        self.download_output_dir = download_output_dir

    def cache_video(self, *, bvid: str, quality_code: str | None = None) -> VideoCacheResponse:
        provider = self.provider_factory.resolve("default")
        detail = self.repository.get_by_bvid(bvid) or provider.get_video(bvid)
        if detail is None:
            raise ProviderUnavailableError("video detail unavailable")

        playback = provider.get_playback_source(bvid, quality_code=quality_code)
        if playback is None:
            raise ProviderUnavailableError("playback source unavailable")

        output_dir = Path(self.download_output_dir).expanduser()
        if not output_dir.is_absolute():
            output_dir = (PROJECT_ROOT / output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self._sanitize_filename(detail.title)}-{playback.selected_quality_label or playback.selected_quality_code}.mp4"
        target = output_dir / filename

        stream, _, _ = provider.stream_playback_source(playback)
        total_bytes = 0
        with target.open("wb") as handle:
            for chunk in stream:
                handle.write(chunk)
                total_bytes += len(chunk)

        self.repository.update_raw_extra(
            bvid,
            {
                "local_cache_path": str(target),
                "local_cache_quality_code": playback.selected_quality_code,
                "local_cache_quality_label": playback.selected_quality_label,
            },
        )
        self.repository.db.commit()

        return VideoCacheResponse(
            bvid=bvid,
            status="completed",
            output_path=str(target),
            quality_code=playback.selected_quality_code,
            quality_label=playback.selected_quality_label,
            bytes_written=total_bytes,
        )

    def _sanitize_filename(self, value: str) -> str:
        compact = re.sub(r"\s+", " ", value).strip()
        return re.sub(r'[\\/:*?"<>|]+', "_", compact)[:120] or "video"
