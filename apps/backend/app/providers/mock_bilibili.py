from datetime import UTC, datetime, timedelta

from app.schemas.video import RecommendationReason, VideoDetail, VideoItem


class MockBilibiliProvider:
    def __init__(self, count: int = 10) -> None:
        self.count = count

    def search(self, query: str, filter_text: str | None = None) -> list[VideoItem]:
        now = datetime.now(UTC)
        items: list[VideoItem] = []
        profiles = [
            ("教程", "系统教程与实战演示", ["tutorial", "guide"], "keyword_match", "教程结果"),
            ("直播切片", "直播切片与高能片段", ["live", "clip"], "keyword_match", "直播切片结果"),
            ("入门", "入门向讲解和知识梳理", ["starter", "guide"], "keyword_match", "入门结果"),
            ("评测", "产品评测与观点整理", ["review", "opinion"], "keyword_match", "评测结果"),
        ]
        for index in range(self.count):
            category, description, extra_tags, reason_code, reason_message = profiles[index % len(profiles)]
            items.append(
                VideoItem(
                    bvid=f"BVMOCK{index:04d}",
                    title=f"{query} {category} Mock Video {index + 1}",
                    author_name=f"Mock UP {index + 1}",
                    cover_url=f"https://placehold.co/640x360?text=Mock+{index + 1}",
                    duration_seconds=600 + index * 15,
                    published_at=now - timedelta(days=index),
                    view_count=10000 + index * 321,
                    like_count=800 + index * 23,
                    summary=f"{description}，关键词 {query}，结果 {index + 1}。",
                    tags=["mock", "bilibili", query.lower(), *extra_tags],
                    match_reasons=[
                        RecommendationReason(
                            code=reason_code,
                            message=reason_message,
                        )
                    ],
                    cached=False,
                )
            )
        return items

    def get_video(self, bvid: str) -> VideoDetail | None:
        try:
            index = int(bvid.replace("BVMOCK", ""))
        except ValueError:
            index = 0
        now = datetime.now(UTC)
        return VideoDetail(
            bvid=bvid,
            title=f"Mock Video {index + 1}",
            author_name=f"Mock UP {index + 1}",
            cover_url=f"https://placehold.co/640x360?text=Mock+{index + 1}",
            duration_seconds=600 + index * 15,
            published_at=now - timedelta(days=index),
            view_count=10000 + index * 321,
            like_count=800 + index * 23,
            summary=f"Mock summary for video {index + 1}.",
            tags=["mock", "bilibili"],
            match_reasons=[
                RecommendationReason(code="keyword_match", message="来自 mock provider")
            ],
            cached=False,
            description="Mock provider detail payload.",
            source_url=f"https://www.bilibili.com/video/{bvid}",
            sync_status="synced",
            last_synced_at=now,
            raw_extra={"partition": "mock"},
        )
