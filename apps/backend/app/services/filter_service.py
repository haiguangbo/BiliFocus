from app.schemas.video import RecommendationReason, VideoItem


class LightweightFilterService:
    def apply(self, items: list[VideoItem], filter_text: str | None) -> list[VideoItem]:
        if not filter_text:
            return items

        normalized = filter_text.strip()
        filtered = items

        if "只看教程" in normalized:
            filtered = [item for item in filtered if self._is_tutorial(item)]
            filtered = [self._append_reason(item, "filter_include", "命中教程筛选") for item in filtered]

        if "排除直播切片" in normalized:
            filtered = [item for item in filtered if not self._is_live_clip(item)]
            filtered = [self._append_reason(item, "filter_exclude_removed", "已排除直播切片") for item in filtered]

        return filtered

    def _is_tutorial(self, item: VideoItem) -> bool:
        haystack = " ".join([item.title, item.summary or "", " ".join(item.tags)]).lower()
        return any(token in haystack for token in ["教程", "guide", "tutorial", "入门"])

    def _is_live_clip(self, item: VideoItem) -> bool:
        haystack = " ".join([item.title, item.summary or "", " ".join(item.tags)]).lower()
        return any(token in haystack for token in ["直播", "切片", "live", "clip"])

    def _append_reason(self, item: VideoItem, code: str, message: str) -> VideoItem:
        reasons = [*item.match_reasons, RecommendationReason(code=code, message=message)]
        return item.model_copy(update={"match_reasons": reasons})
