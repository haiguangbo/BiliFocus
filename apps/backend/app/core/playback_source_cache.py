from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import monotonic

from app.schemas.video import PlaybackSource


_PLAYBACK_SOURCE_TTL_SECONDS = 30.0


@dataclass(slots=True)
class _PlaybackSourceCacheEntry:
    expires_at: float
    source: PlaybackSource


class PlaybackSourceCache:
    def __init__(self) -> None:
        self._entries: dict[str, _PlaybackSourceCacheEntry] = {}
        self._lock = Lock()

    def get(self, *, bvid: str, quality_code: str | None, cid: str | None) -> PlaybackSource | None:
        key = self._build_key(bvid=bvid, quality_code=quality_code, cid=cid)
        now = monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._entries.pop(key, None)
                return None
            return entry.source.model_copy(deep=True)

    def set(self, source: PlaybackSource) -> PlaybackSource:
        key = self._build_key(
            bvid=source.bvid,
            quality_code=source.selected_quality_code,
            cid=source.cid,
        )
        entry = _PlaybackSourceCacheEntry(
            expires_at=monotonic() + _PLAYBACK_SOURCE_TTL_SECONDS,
            source=source.model_copy(deep=True),
        )
        with self._lock:
            self._entries[key] = entry
        return source

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _build_key(self, *, bvid: str, quality_code: str | None, cid: str | None) -> str:
        normalized_quality = (quality_code or "").strip()
        normalized_cid = (cid or "").strip()
        return f"{bvid}:{normalized_cid}:{normalized_quality}"


playback_source_cache = PlaybackSourceCache()
