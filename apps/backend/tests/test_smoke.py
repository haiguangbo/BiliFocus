from datetime import UTC, datetime


def install_stub_provider(monkeypatch) -> None:
    from app.providers.factory import SearchProviderFactory
    from app.schemas.video import PlaybackQualityOption, PlaybackSource, RecommendationReason, VideoDetail, VideoItem

    class StubSearchProvider:
        def search(self, query: str, filter_text: str | None = None) -> list[VideoItem]:
            del filter_text
            lowered_query = query.lower()
            if any(token in lowered_query for token in ["小猪佩奇", "英语", "启蒙", "布鲁依", "bluey", "儿童"]):
                return [
                    VideoItem(
                        bvid="BVKID0000",
                        title="小猪佩奇英文版英语字幕儿童英语启蒙动画",
                        author_name="Kid English",
                        cover_url="https://i0.hdslb.com/bfs/archive/kid-cover.jpg",
                        duration_seconds=1800,
                        published_at=datetime(2026, 3, 20, tzinfo=UTC),
                        view_count=56000,
                        like_count=1800,
                        summary="适合少儿英语启蒙的英文动画，包含日常表达和磨耳朵场景。",
                        tags=["real", "bilibili", "儿童", "英语", "启蒙", "动画"],
                        match_reasons=[RecommendationReason(code="keyword_match", message="标题命中关键词")],
                        cached=False,
                    ),
                    VideoItem(
                        bvid="BVKID0001",
                        title="三分钟速看小猪佩奇",
                        author_name="Clip Channel",
                        cover_url="https://i0.hdslb.com/bfs/archive/kid-cover-2.jpg",
                        duration_seconds=90,
                        published_at=datetime(2026, 3, 21, tzinfo=UTC),
                        view_count=12000,
                        like_count=90,
                        summary="短视频切片。",
                        tags=["real", "bilibili", "直播切片"],
                        match_reasons=[RecommendationReason(code="keyword_match", message="标题命中关键词")],
                        cached=False,
                    ),
                ]
            return [
                VideoItem(
                    bvid="BVREAL0000",
                    title=f"{query} 教程实战",
                    author_name="BiliFocus",
                    cover_url="https://i0.hdslb.com/bfs/archive/demo-cover.jpg",
                    duration_seconds=640,
                    published_at=datetime(2026, 3, 20, tzinfo=UTC),
                    view_count=12000,
                    like_count=680,
                    summary="真实 provider stub 教程视频。",
                    tags=["real", "bilibili", query.lower(), "教程"],
                    match_reasons=[RecommendationReason(code="keyword_match", message="标题命中关键词")],
                    cached=False,
                ),
                VideoItem(
                    bvid="BVREAL0001",
                    title=f"{query} 直播切片",
                    author_name="BiliFocus Live",
                    cover_url="https://i0.hdslb.com/bfs/archive/demo-cover-2.jpg",
                    duration_seconds=300,
                    published_at=datetime(2026, 3, 19, tzinfo=UTC),
                    view_count=8000,
                    like_count=120,
                    summary="用于过滤规则测试。",
                    tags=["real", "bilibili", query.lower(), "直播切片"],
                    match_reasons=[RecommendationReason(code="keyword_match", message="标题命中关键词")],
                    cached=False,
                ),
            ]

        def get_video(self, bvid: str) -> VideoDetail | None:
            if bvid != "BVREAL0000":
                return None
            return VideoDetail(
                bvid=bvid,
                title="python 教程实战",
                author_name="BiliFocus",
                cover_url="https://i0.hdslb.com/bfs/archive/demo-cover.jpg",
                duration_seconds=640,
                published_at=datetime(2026, 3, 20, tzinfo=UTC),
                view_count=12000,
                like_count=680,
                summary="真实 provider stub 教程视频。",
                tags=["real", "bilibili", "python", "教程"],
                match_reasons=[RecommendationReason(code="keyword_match", message="标题命中关键词")],
                cached=False,
                description="真实 provider detail stub。",
                source_url=f"https://www.bilibili.com/video/{bvid}",
                sync_status="synced",
                last_synced_at=datetime(2026, 3, 20, tzinfo=UTC),
                raw_extra={"partition": "教程", "cid": "12345"},
            )

        def get_playback_source(self, bvid: str, quality_code: str | None = None) -> PlaybackSource | None:
            if bvid != "BVREAL0000":
                return None
            selected_quality = quality_code or "64"
            selected_label = "720P 高清" if selected_quality == "64" else "360P 流畅"
            return PlaybackSource(
                bvid=bvid,
                cid="12345",
                selected_quality_code=selected_quality,
                selected_quality_label=selected_label,
                source_url=f"https://media.example.com/{bvid}/{selected_quality}.mp4",
                qualities=[
                    PlaybackQualityOption(code="64", label="720P 高清"),
                    PlaybackQualityOption(code="16", label="360P 流畅"),
                ],
            )

        def stream_playback_source(
            self,
            source: PlaybackSource,
            range_header: str | None = None,
        ) -> tuple[list[bytes], int, dict[str, str]]:
            del range_header
            payload = [f"stream:{source.bvid}:{source.selected_quality_code}".encode("utf-8")]
            return payload, 200, {"Content-Type": "video/mp4", "Accept-Ranges": "bytes"}

    monkeypatch.setattr(SearchProviderFactory, "resolve", lambda self, source: StubSearchProvider())


def test_health_endpoint() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["app"] == "bilifocus-backend"


def test_search_endpoint_returns_real_provider_items(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    install_stub_provider(monkeypatch)

    from app.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/search",
            json={
                "query": "fastapi",
                "filter_text": "只看教程",
                "limit": 5,
                "offset": 0,
                "source": "default",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["query"] == "fastapi"
        assert len(payload["items"]) == 1
        assert payload["items"][0]["bvid"].startswith("BVREAL")

def test_search_endpoint_applies_lightweight_filter(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    install_stub_provider(monkeypatch)

    from app.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/search",
            json={
                "query": "fastapi",
                "filter_text": "只看教程，排除直播切片",
                "limit": 10,
                "offset": 0,
                "source": "default",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] >= 1
        assert all("直播切片" not in item["title"] for item in payload["items"])
        assert any(
            reason["code"] == "filter_include"
            for item in payload["items"]
            for reason in item["match_reasons"]
        )

def test_sync_and_library_flow(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    install_stub_provider(monkeypatch)

    from app.main import app

    with TestClient(app) as client:
        sync_response = client.post(
            "/api/sync/search",
            json={
                "query": "python",
                "filter_text": "只看教程",
                "limit": 3,
                "source": "default",
            },
        )
        assert sync_response.status_code == 200
        sync_payload = sync_response.json()
        assert sync_payload["status"] == "completed"
        assert sync_payload["saved_count"] >= 0

        list_response = client.get("/api/videos")
        assert list_response.status_code == 200
        list_payload = list_response.json()
        assert list_payload["total"] >= 1
        assert list_payload["items"][0]["cached"] is True

        detail_response = client.get("/api/videos/BVREAL0000")
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()
        assert detail_payload["bvid"] == "BVREAL0000"
        assert detail_payload["source_url"].endswith("/BVREAL0000")
        assert detail_payload["sync_status"] == "synced"

        filtered_response = client.get("/api/videos?q=python&sort=published_at")
        assert filtered_response.status_code == 200
        filtered_payload = filtered_response.json()
        assert filtered_payload["total"] >= 1


def test_preferences_roundtrip() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        update_response = client.put(
            "/api/preferences",
            json={
                "default_search_limit": 12,
                "default_source": "default",
                "default_filter_text": "排除直播切片",
                "bilibili_cookie": "SESSDATA=test-cookie",
                "download_output_dir": "./data/downloads",
                "theme": "system",
                "language": "zh-CN",
                "library_sort": "recent",
                "hide_watched_placeholder": False,
            },
        )
        assert update_response.status_code == 200
        get_response = client.get("/api/preferences")
        assert get_response.status_code == 200
        payload = get_response.json()
        assert payload["default_search_limit"] == 12
        assert payload["default_filter_text"] == "排除直播切片"
        assert payload["bilibili_cookie"] == "SESSDATA=test-cookie"
        assert payload["download_output_dir"] == "./data/downloads"


def test_playback_endpoint_returns_quality_specific_stream(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    install_stub_provider(monkeypatch)

    from app.main import app

    with TestClient(app) as client:
        playback_response = client.get("/api/videos/BVREAL0000/playback?quality=16")
        assert playback_response.status_code == 200
        playback_payload = playback_response.json()
        assert playback_payload["selected_quality_code"] == "16"
        assert playback_payload["selected_quality_label"] == "360P 流畅"
        assert playback_payload["stream_url"].endswith("/api/videos/BVREAL0000/stream?quality=16")

        stream_response = client.get("/api/videos/BVREAL0000/stream?quality=16")
        assert stream_response.status_code == 200
        assert stream_response.headers["content-type"].startswith("video/mp4")
        assert stream_response.content == b"stream:BVREAL0000:16"


def test_playback_progress_endpoint_updates_local_record(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    install_stub_provider(monkeypatch)

    from app.main import app

    with TestClient(app) as client:
        client.post(
            "/api/sync/search",
            json={
                "query": "python",
                "filter_text": "只看教程",
                "limit": 3,
                "source": "default",
            },
        )
        response = client.post(
            "/api/videos/BVREAL0000/playback-progress",
            json={
                "position_seconds": 128.4,
                "duration_seconds": 640,
                "completed": False,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["progress_percent"] > 0

        detail_response = client.get("/api/videos/BVREAL0000")
        detail_payload = detail_response.json()
        assert detail_payload["raw_extra"]["playback_position_seconds"] == "128.40"
        assert detail_payload["raw_extra"]["playback_progress_percent"] == f"{payload['progress_percent']:.2f}"

        list_response = client.get("/api/videos")
        list_payload = list_response.json()
        matching = next(item for item in list_payload["items"] if item["bvid"] == "BVREAL0000")
        assert matching["playback_position_seconds"] == 128.4
        assert matching["playback_progress_percent"] == payload["progress_percent"]


def test_delete_video_endpoint_removes_local_record(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    install_stub_provider(monkeypatch)

    from app.main import app

    with TestClient(app) as client:
        client.post(
            "/api/sync/search",
            json={
                "query": "python",
                "filter_text": "只看教程",
                "limit": 3,
                "source": "default",
            },
        )
        delete_response = client.delete("/api/videos/BVREAL0000")
        assert delete_response.status_code == 200
        assert delete_response.json()["status"] == "deleted"

        detail_response = client.get("/api/videos/BVREAL0000")
        assert detail_response.status_code == 404


def test_curation_rewrites_longform_objective_into_usable_intent(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    install_stub_provider(monkeypatch)
    from app.services.curation_service import CurationService

    monkeypatch.setattr(
        CurationService,
        "_rewrite_objective",
        lambda self, objective, extra_requirements: "少儿 英语 启蒙 动画；小猪佩奇；布鲁依",
    )
    monkeypatch.setattr(CurationService, "_llm_keywords", lambda self, objective, extra_requirements, max_keywords: [])

    from app.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/curation/run",
            json={
                "objective": "我家里的小朋友现在需要学习英语，现在需要一些质量上乘的英语动画，如小猪佩奇、布鲁依等等",
                "extra_requirements": "",
                "max_keywords": 5,
                "limit_per_keyword": 5,
                "sync_accepted": False,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["reviewed_count"] >= 1
        assert payload["accepted_count"] >= 1
        assert any("小猪佩奇" in keyword or "英语" in keyword for keyword in payload["recommended_keywords"])


def test_rewrite_library_metadata_endpoint(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    install_stub_provider(monkeypatch)

    from app.main import app
    from app.services.metadata_rewrite_service import MetadataRewriteService

    monkeypatch.setattr(
        MetadataRewriteService,
        "_rewrite_item",
        lambda self, item: {
            "summary": "结构化摘要：适合少儿英语启蒙。",
            "tags": ["英语提升", "少儿内容", "动画素材"],
            "raw_extra_updates": {
                "structured_summary": "结构化摘要：适合少儿英语启蒙。",
                "rewrite_audience": "少儿学习者",
                "rewrite_focus": "英语启蒙,动画磨耳朵",
                "rewrite_quality_notes": "时长较完整",
                "rewrite_last_run_at": "2026-03-23T00:00:00Z",
            },
        },
    )

    with TestClient(app) as client:
        client.post(
            "/api/sync/search",
            json={
                "query": "儿童英语",
                "filter_text": "",
                "limit": 3,
                "source": "default",
            },
        )
        rewrite_response = client.post("/api/videos/rewrite-metadata", json={"limit": 10, "tag": None})
        assert rewrite_response.status_code == 200
        rewrite_payload = rewrite_response.json()
        assert rewrite_payload["rewritten_count"] >= 1

        detail_response = client.get("/api/videos/BVREAL0000")
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()
        assert detail_payload["summary"] == "结构化摘要：适合少儿英语启蒙。"
        assert "英语提升" in detail_payload["tags"]
        assert detail_payload["raw_extra"]["rewrite_audience"] == "少儿学习者"
