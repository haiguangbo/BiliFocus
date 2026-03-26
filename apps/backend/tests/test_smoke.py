from datetime import UTC, datetime


class _StubHTTPResponse:
    def __init__(self, body: bytes, *, status: int = 200, headers: dict[str, str] | None = None) -> None:
        self._body = body
        self._cursor = 0
        self.status = status
        self.headers = headers or {}

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._body) - self._cursor
        chunk = self._body[self._cursor:self._cursor + size]
        self._cursor += len(chunk)
        return chunk

    def close(self) -> None:
        return None


def install_stub_provider(monkeypatch) -> None:
    from app.core.playback_source_cache import playback_source_cache
    from app.providers.factory import SearchProviderFactory
    from app.schemas.video import PlaybackQualityOption, PlaybackSource, RecommendationReason, VideoDetail, VideoItem

    playback_source_cache.clear()

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


def install_counting_playback_provider(monkeypatch, counters: dict[str, int]) -> None:
    from app.core.playback_source_cache import playback_source_cache
    from app.providers.factory import SearchProviderFactory
    from app.schemas.video import PlaybackQualityOption, PlaybackSource, RecommendationReason, VideoDetail

    playback_source_cache.clear()

    class CountingPlaybackProvider:
        def get_video(self, bvid: str) -> VideoDetail | None:
            counters["get_video"] = counters.get("get_video", 0) + 1
            if bvid != "BVREAL0000":
                return None
            return VideoDetail(
                bvid=bvid,
                title="python 教程实战",
                author_name="BiliFocus",
                duration_seconds=640,
                published_at=datetime(2026, 3, 20, tzinfo=UTC),
                view_count=12000,
                like_count=680,
                summary="真实 provider detail stub。",
                tags=["real", "bilibili", "python", "教程"],
                match_reasons=[RecommendationReason(code="keyword_match", message="标题命中关键词")],
                cached=False,
                description="真实 provider detail stub。",
                source_url=f"https://www.bilibili.com/video/{bvid}",
                sync_status="synced",
                last_synced_at=datetime(2026, 3, 20, tzinfo=UTC),
                raw_extra={"partition": "教程", "cid": "12345", "aid": "777"},
            )

        def get_playback_source(self, bvid: str, quality_code: str | None = None, cid: str | None = None) -> PlaybackSource | None:
            counters["get_playback_source"] = counters.get("get_playback_source", 0) + 1
            if bvid != "BVREAL0000":
                return None
            selected_quality = quality_code or "64"
            return PlaybackSource(
                bvid=bvid,
                cid=cid or "12345",
                selected_quality_code=selected_quality,
                selected_quality_label="720P 高清" if selected_quality == "64" else "360P 流畅",
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
            counters["stream_playback_source"] = counters.get("stream_playback_source", 0) + 1
            return [f"stream:{source.bvid}:{source.selected_quality_code}".encode("utf-8")], 200, {"Content-Type": "video/mp4"}

    monkeypatch.setattr(SearchProviderFactory, "resolve", lambda self, source: CountingPlaybackProvider())


def test_bilibili_provider_streams_multi_segment_source() -> None:
    from app.providers.bilibili_web import BilibiliWebSearchProvider
    from app.schemas.video import PlaybackSegment, PlaybackSource

    provider = BilibiliWebSearchProvider(
        api_base_url="https://api.bilibili.com",
        referer="https://www.bilibili.com",
        user_agent="test-agent",
        timeout_seconds=3,
        page_size=20,
    )

    payloads = {
        "https://media.example.com/seg-1.mp4": b"hello ",
        "https://media.example.com/seg-2.mp4": b"world",
    }

    def fake_open_stream(url: str, *, range_header: str | None = None):
        assert range_header is None
        return _StubHTTPResponse(
            payloads[url],
            headers={"Content-Type": "video/mp4", "Content-Length": str(len(payloads[url]))},
        )

    provider._open_stream = fake_open_stream  # type: ignore[method-assign]
    source = PlaybackSource(
        bvid="BVSEG0001",
        cid="123",
        selected_quality_code="64",
        selected_quality_label="720P 高清",
        source_url="https://media.example.com/seg-1.mp4",
        segments=[
            PlaybackSegment(url="https://media.example.com/seg-1.mp4", size=6),
            PlaybackSegment(url="https://media.example.com/seg-2.mp4", size=5),
        ],
        total_size=11,
    )

    stream, status_code, headers = provider.stream_playback_source(source)

    assert status_code == 200
    assert headers["Content-Length"] == "11"
    assert headers["Accept-Ranges"] == "bytes"
    assert b"".join(stream) == b"hello world"


def test_bilibili_provider_maps_range_requests_across_segments() -> None:
    from app.providers.bilibili_web import BilibiliWebSearchProvider
    from app.schemas.video import PlaybackSegment, PlaybackSource

    provider = BilibiliWebSearchProvider(
        api_base_url="https://api.bilibili.com",
        referer="https://www.bilibili.com",
        user_agent="test-agent",
        timeout_seconds=3,
        page_size=20,
    )

    payloads = {
        "https://media.example.com/seg-1.mp4": b"hello ",
        "https://media.example.com/seg-2.mp4": b"world",
    }
    requested_ranges: list[tuple[str, str | None]] = []

    def fake_open_stream(url: str, *, range_header: str | None = None):
        requested_ranges.append((url, range_header))
        body = payloads[url]
        if range_header is None:
            return _StubHTTPResponse(body, headers={"Content-Type": "video/mp4", "Content-Length": str(len(body))})
        _, value = range_header.split("=", 1)
        start_text, end_text = value.split("-", 1)
        start = int(start_text)
        end = int(end_text)
        chunk = body[start:end + 1]
        return _StubHTTPResponse(
            chunk,
            status=206,
            headers={
                "Content-Type": "video/mp4",
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {start}-{end}/{len(body)}",
                "Accept-Ranges": "bytes",
            },
        )

    provider._open_stream = fake_open_stream  # type: ignore[method-assign]
    source = PlaybackSource(
        bvid="BVSEG0002",
        cid="123",
        selected_quality_code="64",
        selected_quality_label="720P 高清",
        source_url="https://media.example.com/seg-1.mp4",
        segments=[
            PlaybackSegment(url="https://media.example.com/seg-1.mp4", size=6),
            PlaybackSegment(url="https://media.example.com/seg-2.mp4", size=5),
        ],
        total_size=11,
    )

    stream, status_code, headers = provider.stream_playback_source(source, range_header="bytes=4-8")

    assert status_code == 206
    assert headers["Content-Length"] == "5"
    assert headers["Content-Range"] == "bytes 4-8/11"
    assert b"".join(stream) == b"o wor"
    assert requested_ranges == [
        ("https://media.example.com/seg-1.mp4", "bytes=4-5"),
        ("https://media.example.com/seg-2.mp4", "bytes=0-2"),
    ]


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


def test_curation_flow_uses_crewai_agents(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    monkeypatch.setenv("CREWAI_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")

    install_stub_provider(monkeypatch)

    import app.services.crewai_curation_service as crewai_module
    from app.main import app

    class FakeBaseLLM:
        def __init__(
            self,
            *,
            model: str,
            temperature: float,
            api_key: str,
            base_url: str,
            provider: str,
        ) -> None:
            self.model = model
            self.temperature = temperature
            self.api_key = api_key
            self.base_url = base_url
            self.provider = provider

    class FakeAgent:
        def __init__(self, **kwargs) -> None:
            self.role = kwargs["role"]
            self.goal = kwargs["goal"]
            self.backstory = kwargs["backstory"]
            self.verbose = kwargs["verbose"]
            self.allow_delegation = kwargs["allow_delegation"]
            self.max_iter = kwargs["max_iter"]
            self.llm = kwargs["llm"]

    class FakeTask:
        def __init__(self, **kwargs) -> None:
            self.description = kwargs["description"]
            self.expected_output = kwargs["expected_output"]
            self.agent = kwargs["agent"]
            self.output_pydantic = kwargs["output_pydantic"]
            self.output = None

    class FakeCrewResult:
        def __init__(self, model) -> None:
            self.pydantic = model
            self.raw = model.model_dump_json()

    class FakeCrew:
        def __init__(self, *, agents, tasks, process, verbose) -> None:
            self.agents = agents
            self.tasks = tasks
            self.process = process
            self.verbose = verbose

        def kickoff(self):
            task = self.tasks[0]
            model_cls = task.output_pydantic
            if model_cls.__name__ == "KeywordPlan":
                model = model_cls(keywords=["python 架构", "python 工程化", "fastapi 实战"])
            elif model_cls.__name__ == "ReviewPlan":
                model = model_cls(
                    decisions=[
                        {"bvid": "BVREAL0000", "keep": True, "reason": "教程内容完整"},
                        {"bvid": "BVREAL0001", "keep": False, "reason": "直播切片噪声"},
                    ]
                )
            elif model_cls.__name__ == "CategoryPlan":
                model = model_cls(items=[{"bvid": "BVREAL0000", "categories": ["Python", "后端"]}])
            else:
                raise AssertionError(f"unexpected CrewAI model: {model_cls.__name__}")

            task.output = type("FakeTaskOutput", (), {"pydantic": model})()
            return FakeCrewResult(model)

    class FakeProcess:
        sequential = "sequential"

    monkeypatch.setattr(crewai_module, "BaseLLM", FakeBaseLLM)
    monkeypatch.setattr(crewai_module, "CrewAIBaseLLM", FakeBaseLLM)
    monkeypatch.setattr(crewai_module, "Agent", FakeAgent)
    monkeypatch.setattr(crewai_module, "Task", FakeTask)
    monkeypatch.setattr(crewai_module, "Crew", FakeCrew)
    monkeypatch.setattr(crewai_module, "Process", FakeProcess)

    with TestClient(app) as client:
        response = client.post(
            "/api/curation/run",
            json={
                "objective": "学习 Python 后端架构",
                "extra_requirements": "只看教程，排除直播切片",
                "max_keywords": 3,
                "limit_per_keyword": 3,
                "sync_accepted": True,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["recommended_keywords"] == ["python 架构", "python 工程化", "fastapi 实战"]
    assert payload["accepted_count"] >= 1
    assert payload["pipeline_trace"]["planner"]["agent"] == "crewai.keyword_planner"
    assert payload["pipeline_trace"]["reviewer"]["agent"] == "crewai.content_reviewer"
    assert payload["pipeline_trace"]["classifier"]["agent"] == "crewai.content_classifier"


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


def test_playback_source_is_reused_between_playback_and_stream_requests(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    counters: dict[str, int] = {}
    install_counting_playback_provider(monkeypatch, counters)

    from app.main import app

    with TestClient(app) as client:
        playback_response = client.get("/api/videos/BVREAL0000/playback?quality=16&cid=12345")
        assert playback_response.status_code == 200

        stream_response = client.get("/api/videos/BVREAL0000/stream?quality=16&cid=12345")
        assert stream_response.status_code == 200
        assert stream_response.content == b"stream:BVREAL0000:16"

    assert counters["get_playback_source"] == 1
    assert counters["stream_playback_source"] == 1
    assert counters.get("get_video", 0) == 0


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
