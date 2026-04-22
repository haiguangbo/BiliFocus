from typing import Protocol

from collections.abc import Iterable

from app.schemas.video import PlaybackSource, VideoDetail, VideoItem


class SearchProvider(Protocol):
    def search(self, query: str, filter_text: str | None = None) -> list[VideoItem]:
        ...

    def get_video(self, bvid: str) -> VideoDetail | None:
        ...

    def get_playback_source(
        self,
        bvid: str,
        quality_code: str | None = None,
        cid: str | None = None,
    ) -> PlaybackSource | None:
        ...

    def stream_playback_source(
        self,
        source: PlaybackSource,
        range_header: str | None = None,
    ) -> tuple[Iterable[bytes], int, dict[str, str]]:
        ...


class ProviderUnavailableError(RuntimeError):
    pass
