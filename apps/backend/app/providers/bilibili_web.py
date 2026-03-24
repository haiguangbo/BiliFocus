import html
import json
import re
import time
from datetime import UTC, datetime
from hashlib import md5
from http.cookiejar import CookieJar
from http.cookies import SimpleCookie
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

from app.providers.base import ProviderUnavailableError
from app.schemas.video import PlaybackQualityOption, PlaybackSource, RecommendationReason, VideoDetail, VideoItem


class BilibiliWebSearchProvider:
    _MIXIN_KEY_ENC_TAB = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
        27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
        37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
        22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
    ]

    def __init__(
        self,
        *,
        api_base_url: str,
        referer: str,
        user_agent: str,
        timeout_seconds: float,
        page_size: int,
        cookie: str = "",
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.referer = referer
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.page_size = page_size
        self.manual_cookie_header = self._normalize_manual_cookie(cookie)
        self.cookie_jar = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))

    def search(self, query: str, filter_text: str | None = None) -> list[VideoItem]:
        del filter_text
        self._bootstrap_web_context()
        params = self._sign_wbi_params(
            {
                "search_type": "video",
                "keyword": query,
                "page": 1,
                "page_size": self.page_size,
            }
        )
        try:
            payload = self._request_json(f"{self.api_base_url}/x/web-interface/wbi/search/type?{params}")
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderUnavailableError("bilibili web search request failed") from exc

        if payload.get("code") != 0:
            raise ProviderUnavailableError(f"bilibili web search returned code {payload.get('code')}")

        if self._is_voucher_only_response(payload):
            raise ProviderUnavailableError("bilibili search is currently blocked by upstream risk control; configure a valid Bilibili cookie and retry")

        result = self._extract_video_search_items(payload)
        if not result:
            params = self._sign_wbi_params({"keyword": query})
            try:
                fallback_payload = self._request_json(f"{self.api_base_url}/x/web-interface/wbi/search/all/v2?{params}")
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
                raise ProviderUnavailableError("bilibili web search fallback request failed") from exc
            if fallback_payload.get("code") != 0:
                raise ProviderUnavailableError(f"bilibili web search fallback returned code {fallback_payload.get('code')}")
            if self._is_voucher_only_response(fallback_payload):
                raise ProviderUnavailableError("bilibili search is currently blocked by upstream risk control; configure a valid Bilibili cookie and retry")
            result = self._extract_video_search_items(fallback_payload)
        return [self._to_video_item(item, query) for item in result if item.get("bvid")]

    def get_video(self, bvid: str) -> VideoDetail | None:
        self._bootstrap_web_context()
        params = urlencode({"bvid": bvid})
        try:
            payload = self._request_json(f"{self.api_base_url}/x/web-interface/view?{params}")
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderUnavailableError("bilibili web detail request failed") from exc

        if payload.get("code") != 0:
            raise ProviderUnavailableError(f"bilibili web detail returned code {payload.get('code')}")

        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        return self._to_video_detail(data)

    def get_playback_source(
        self,
        bvid: str,
        quality_code: str | None = None,
        cid: str | None = None,
    ) -> PlaybackSource | None:
        detail = self.get_video(bvid)
        if detail is None:
            return None

        aid = detail.raw_extra.get("aid")
        resolved_cid = cid or detail.raw_extra.get("cid")
        if not aid or not resolved_cid:
            return None

        try:
            playurl_payload = self._fetch_progressive_playurl(
                aid=int(aid),
                bvid=bvid,
                cid=int(resolved_cid),
                quality_code=int(quality_code) if quality_code else None,
            )
        except ProviderUnavailableError:
            return None

        data = playurl_payload.get("data")
        if not isinstance(data, dict):
            return None

        durl = data.get("durl") if isinstance(data.get("durl"), list) else []
        if not durl:
            return None

        url = durl[0].get("url")
        if not isinstance(url, str) or not url:
            return None

        accept_quality = data.get("accept_quality") if isinstance(data.get("accept_quality"), list) else []
        accept_description = data.get("accept_description") if isinstance(data.get("accept_description"), list) else []
        selected_quality = str(data.get("quality") or quality_code or "")
        qualities = [
            PlaybackQualityOption(code=str(code), label=str(accept_description[index]) if index < len(accept_description) else str(code))
            for index, code in enumerate(accept_quality)
        ]

        return PlaybackSource(
            bvid=bvid,
            cid=str(resolved_cid),
            selected_quality_code=selected_quality,
            selected_quality_label=self._match_quality_label(selected_quality, accept_quality, accept_description),
            source_url=url,
            qualities=qualities,
        )

    def stream_playback_source(
        self,
        source: PlaybackSource,
        range_header: str | None = None,
    ) -> tuple[object, int, dict[str, str]]:
        request = Request(source.source_url, headers=self._build_headers(accept="video/*,*/*"))
        if range_header:
            request.add_header("Range", range_header)
        try:
            response = self.opener.open(request, timeout=self.timeout_seconds)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise ProviderUnavailableError("bilibili playback stream request failed") from exc

        status_code = getattr(response, "status", 200)
        headers = {
            key: value
            for key, value in response.headers.items()
            if key.lower() in {"content-type", "content-length", "content-range", "accept-ranges"}
        }

        def iterator():
            try:
                while True:
                    chunk = response.read(1024 * 128)
                    if not chunk:
                        break
                    yield chunk
            finally:
                response.close()

        return iterator(), status_code, headers

    def _to_video_item(self, item: dict, query: str) -> VideoItem:
        published_at = None
        pubdate = item.get("pubdate")
        if isinstance(pubdate, int | float):
            published_at = datetime.fromtimestamp(pubdate, tz=UTC)

        summary = self._clean_text(item.get("description") or item.get("hit_columns") or "")
        if not summary:
            summary = self._clean_text(item.get("title") or "")

        tags = [
            "real",
            "bilibili",
            query.lower(),
        ]
        typename = self._clean_text(item.get("typename") or "")
        if typename:
            tags.append(typename.lower())

        return VideoItem(
            bvid=item["bvid"],
            title=self._clean_text(item.get("title") or ""),
            author_name=self._clean_text(item.get("author") or "未知 UP 主"),
            cover_url=self._normalize_cover_url(item.get("pic")),
            duration_seconds=self._parse_duration(item.get("duration")),
            published_at=published_at,
            view_count=self._parse_count(item.get("play")),
            like_count=self._parse_count(item.get("like")),
            summary=summary,
            tags=tags,
            match_reasons=[
                RecommendationReason(code="keyword_match", message="来自真实 Bilibili 搜索")
            ],
            cached=False,
        )

    def _extract_video_search_items(self, payload: dict) -> list[dict]:
        data = payload.get("data")
        if not isinstance(data, dict):
            return []

        result = data.get("result")
        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, dict) and "result_type" in first:
                for module in result:
                    if isinstance(module, dict) and module.get("result_type") == "video":
                        module_items = module.get("data")
                        if isinstance(module_items, list):
                            return [item for item in module_items if isinstance(item, dict)]
                return []
            return [item for item in result if isinstance(item, dict)]

        return []

    def _is_voucher_only_response(self, payload: dict) -> bool:
        data = payload.get("data")
        if not isinstance(data, dict):
            return False
        keys = set(data.keys())
        return bool(keys) and keys <= {"v_voucher"}

    def _to_video_detail(self, item: dict) -> VideoDetail:
        published_at = None
        pubdate = item.get("pubdate")
        if isinstance(pubdate, int | float):
            published_at = datetime.fromtimestamp(pubdate, tz=UTC)

        stat = item.get("stat") if isinstance(item.get("stat"), dict) else {}
        owner = item.get("owner") if isinstance(item.get("owner"), dict) else {}
        raw_extra = {
            "provider": "bilibili-web",
            "partition": self._clean_text(item.get("tname") or ""),
            "reply_count": str(stat.get("reply") or 0),
        }
        ugc_season = item.get("ugc_season") if isinstance(item.get("ugc_season"), dict) else {}
        season_id = ugc_season.get("id") or item.get("season_id")
        if season_id:
            raw_extra["collection_root_id"] = str(season_id)
        collection_root_title = self._clean_text(ugc_season.get("title") or "")
        if collection_root_title:
            raw_extra["collection_root_title"] = collection_root_title
        episode_tree = self._build_episode_tree(item)
        if episode_tree:
            raw_extra["episode_tree_json"] = json.dumps(episode_tree, ensure_ascii=False)
        episode_playlist = self._build_episode_playlist(item)
        if episode_playlist:
            raw_extra["episode_playlist_json"] = json.dumps(episode_playlist, ensure_ascii=False)
        raw_extra.update(self._get_stream_metadata(item))

        return VideoDetail(
            bvid=self._clean_text(item.get("bvid") or ""),
            title=self._clean_text(item.get("title") or ""),
            author_name=self._clean_text(owner.get("name") or "未知 UP 主"),
            cover_url=self._normalize_cover_url(item.get("pic")),
            duration_seconds=self._parse_duration(item.get("duration")),
            published_at=published_at,
            view_count=self._parse_count(stat.get("view")),
            like_count=self._parse_count(stat.get("like")),
            summary=self._clean_text(item.get("desc") or ""),
            tags=["real", "bilibili", raw_extra["partition"].lower()] if raw_extra["partition"] else ["real", "bilibili"],
            match_reasons=[RecommendationReason(code="keyword_match", message="来自真实 Bilibili 详情")],
            cached=False,
            description=self._clean_text(item.get("desc") or ""),
            source_url=f"https://www.bilibili.com/video/{self._clean_text(item.get('bvid') or '')}",
            sync_status="synced",
            last_synced_at=datetime.now(UTC),
            raw_extra=raw_extra,
        )

    def _clean_text(self, value: object) -> str:
        if isinstance(value, list):
            value = " ".join(str(entry) for entry in value)
        elif isinstance(value, dict):
            value = " ".join(f"{key}:{entry}" for key, entry in value.items())
        text = re.sub(r"<[^>]+>", "", str(value or ""))
        return html.unescape(text).strip()

    def _normalize_cover_url(self, value: str | None) -> str | None:
        if not value:
            return None
        if value.startswith("//"):
            return f"https:{value}"
        if value.startswith("http://"):
            return value.replace("http://", "https://", 1)
        return value

    def _parse_duration(self, value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        text = str(value).strip()
        if not text:
            return None
        if text.isdigit():
            return int(text)
        parts = [segment for segment in text.split(":") if segment.isdigit()]
        if not parts:
            return None
        total = 0
        for part in parts:
            total = total * 60 + int(part)
        return total

    def _parse_count(self, value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        text = str(value).strip()
        if not text:
            return None
        if text.isdigit():
            return int(text)
        normalized = text.replace(",", "")
        if normalized.endswith("万"):
            try:
                return int(float(normalized[:-1]) * 10000)
            except ValueError:
                return None
        match = re.search(r"\d+(?:\.\d+)?", normalized)
        if match:
            try:
                return int(float(match.group(0)))
            except ValueError:
                return None
        return None

    def _bootstrap_web_context(self) -> None:
        if any(cookie.name == "buvid3" for cookie in self.cookie_jar):
            return
        try:
            self._request_text(self.referer)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderUnavailableError("failed to bootstrap bilibili web cookies") from exc

    def _request_json(self, url: str) -> dict:
        request = Request(url, headers=self._build_headers())
        with self.opener.open(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _request_text(self, url: str) -> str:
        request = Request(url, headers=self._build_headers(accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"))
        with self.opener.open(request, timeout=self.timeout_seconds) as response:
            return response.read().decode("utf-8", errors="ignore")

    def _build_headers(self, accept: str = "application/json") -> dict[str, str]:
        headers = {
            "User-Agent": self.user_agent,
            "Referer": self.referer,
            "Accept": accept,
            "Origin": self._origin_from_url(self.referer),
        }
        cookie_header = self._cookie_header()
        if cookie_header:
            headers["Cookie"] = cookie_header
        return headers

    def _cookie_header(self) -> str:
        parts = [f"{cookie.name}={cookie.value}" for cookie in self.cookie_jar]
        if self.manual_cookie_header:
            parts.append(self.manual_cookie_header)
        return "; ".join(part for part in parts if part)

    def _sign_wbi_params(self, params: dict[str, object]) -> str:
        img_key, sub_key = self._get_wbi_keys()
        mixin_key = self._get_mixin_key(img_key + sub_key)
        signed_params = {key: self._sanitize_wbi_value(value) for key, value in params.items()}
        signed_params["wts"] = str(round(time.time()))
        canonical_query = "&".join(
            f"{quote(str(key), safe='')}={quote(str(signed_params[key]), safe='~-._')}"
            for key in sorted(signed_params)
        )
        w_rid = md5(f"{canonical_query}{mixin_key}".encode("utf-8")).hexdigest()
        request_params = dict(signed_params)
        request_params["w_rid"] = w_rid
        return urlencode(request_params)

    def _get_wbi_keys(self) -> tuple[str, str]:
        payload = self._request_json(f"{self.api_base_url}/x/web-interface/nav")
        data = payload.get("data", {})
        wbi_img = data.get("wbi_img", {}) if isinstance(data, dict) else {}
        img_url = wbi_img.get("img_url") if isinstance(wbi_img, dict) else None
        sub_url = wbi_img.get("sub_url") if isinstance(wbi_img, dict) else None
        img_key = self._extract_wbi_key(img_url)
        sub_key = self._extract_wbi_key(sub_url)
        if not img_key or not sub_key:
            raise ProviderUnavailableError("bilibili nav did not return wbi keys")
        return img_key, sub_key

    def _extract_wbi_key(self, value: object) -> str | None:
        if not isinstance(value, str) or not value:
            return None
        path = urlsplit(value).path
        filename = path.rsplit("/", 1)[-1]
        return filename.split(".", 1)[0] or None

    def _get_mixin_key(self, raw_key: str) -> str:
        return "".join(raw_key[index] for index in self._MIXIN_KEY_ENC_TAB)[:32]

    def _sanitize_wbi_value(self, value: object) -> str:
        return "".join(char for char in str(value) if char not in "!'()*")

    def _origin_from_url(self, value: str) -> str:
        parts = urlsplit(value)
        return f"{parts.scheme}://{parts.netloc}"

    def _normalize_manual_cookie(self, value: str) -> str:
        cookie = value.strip()
        if not cookie:
            return ""
        if "=" not in cookie:
            return f"SESSDATA={cookie}"
        parsed = SimpleCookie()
        parsed.load(cookie)
        if parsed:
            return "; ".join(f"{key}={morsel.value}" for key, morsel in parsed.items())
        return cookie

    def _get_stream_metadata(self, item: dict) -> dict[str, str]:
        aid = item.get("aid")
        cid = item.get("cid")
        if not aid or not cid:
            return {}

        metadata = {
            "aid": str(aid),
            "cid": str(cid),
            "auth_cookie_configured": "true" if self.manual_cookie_header else "false",
        }
        try:
            playurl_payload = self._fetch_playurl(
                aid=int(aid),
                bvid=self._clean_text(item.get("bvid") or ""),
                cid=int(cid),
            )
        except ProviderUnavailableError:
            return metadata

        data = playurl_payload.get("data")
        if not isinstance(data, dict):
            return metadata

        accept_quality = data.get("accept_quality") if isinstance(data.get("accept_quality"), list) else []
        accept_description = data.get("accept_description") if isinstance(data.get("accept_description"), list) else []
        quality = data.get("quality")
        metadata.update(
            {
                "stream_best_quality_code": str(quality or ""),
                "stream_best_quality_label": self._match_quality_label(quality, accept_quality, accept_description),
                "stream_accept_quality_codes": ",".join(str(entry) for entry in accept_quality),
                "stream_accept_quality_labels": ",".join(str(entry) for entry in accept_description),
            }
        )
        return metadata

    def _build_episode_playlist(self, item: dict) -> list[dict[str, str]]:
        playlist: list[dict[str, str]] = []
        ugc_season = item.get("ugc_season")
        if isinstance(ugc_season, dict):
            sections = ugc_season.get("sections")
            if isinstance(sections, list):
                for section in sections:
                    episodes = section.get("episodes") if isinstance(section, dict) else None
                    if not isinstance(episodes, list):
                        continue
                    for index, episode in enumerate(episodes, start=1):
                        if not isinstance(episode, dict):
                            continue
                        bvid = self._clean_text(episode.get("bvid") or "")
                        if not bvid:
                            continue
                        playlist.append(
                            {
                                "bvid": bvid,
                                "cid": str(episode.get("cid") or ""),
                                "index": str(episode.get("title") or index),
                                "label": self._clean_text(episode.get("title") or f"EP{index}"),
                                "title": self._clean_text(
                                    episode.get("title_long")
                                    or episode.get("share_copy")
                                    or episode.get("title")
                                    or f"第{index}集"
                                ),
                            }
                    )
        if playlist:
            return playlist

        pages = item.get("pages")
        if not isinstance(pages, list):
            return playlist
        for index, page in enumerate(pages, start=1):
            if not isinstance(page, dict):
                continue
            cid = str(page.get("cid") or "")
            if not cid:
                continue
            page_no = page.get("page") or index
            playlist.append(
                {
                    "bvid": self._clean_text(item.get("bvid") or ""),
                    "cid": cid,
                    "index": str(page_no),
                    "label": f"P{page_no}",
                    "title": self._clean_text(page.get("part") or f"第{page_no}P"),
                }
            )
        return playlist

    def _build_episode_tree(self, item: dict) -> list[dict[str, object]]:
        ugc_season = item.get("ugc_season")
        if isinstance(ugc_season, dict):
            season_id = ugc_season.get("id") or item.get("season_id")
            owner = item.get("owner") if isinstance(item.get("owner"), dict) else {}
            mid = owner.get("mid")
            collection_title = self._clean_text(
                ugc_season.get("title") or item.get("title") or "合集"
            )
            if season_id and mid:
                fetched = self._fetch_collection_tree(mid=int(mid), season_id=int(season_id), collection_title=collection_title)
                if fetched:
                    return fetched

            sections = ugc_season.get("sections")
            if isinstance(sections, list):
                groups: list[dict[str, object]] = []
                for section_index, section in enumerate(sections, start=1):
                    if not isinstance(section, dict):
                        continue
                    episodes = section.get("episodes")
                    if not isinstance(episodes, list):
                        continue
                    children: list[dict[str, str]] = []
                    for episode_index, episode in enumerate(episodes, start=1):
                        if not isinstance(episode, dict):
                            continue
                        bvid = self._clean_text(episode.get("bvid") or "")
                        if not bvid:
                            continue
                        children.append(
                            {
                                "bvid": bvid,
                                "cid": str(episode.get("cid") or ""),
                                "index": str(episode.get("title") or episode_index),
                                "label": self._clean_text(episode.get("title") or f"EP{episode_index}"),
                                "title": self._clean_text(
                                    episode.get("title_long")
                                    or episode.get("share_copy")
                                    or episode.get("title")
                                    or f"第{episode_index}集"
                                ),
                            }
                        )
                    if children:
                        groups.append(
                            {
                                "title": self._clean_text(section.get("title") or f"分组 {section_index}"),
                                "children": children,
                            }
                        )
                if groups:
                    return groups

        pages = item.get("pages")
        if isinstance(pages, list) and len(pages) > 1:
            children: list[dict[str, str]] = []
            for index, page in enumerate(pages, start=1):
                if not isinstance(page, dict):
                    continue
                cid = str(page.get("cid") or "")
                if not cid:
                    continue
                page_no = page.get("page") or index
                children.append(
                    {
                        "bvid": self._clean_text(item.get("bvid") or ""),
                        "cid": cid,
                        "index": str(page_no),
                        "label": f"P{page_no}",
                        "title": self._clean_text(page.get("part") or f"第{page_no}P"),
                    }
                )
            if children:
                return [{"title": "分P选集", "children": children}]
        return []

    def _fetch_collection_tree(self, *, mid: int, season_id: int, collection_title: str) -> list[dict[str, object]]:
        page_num = 1
        children: list[dict[str, str]] = []
        while True:
            params = urlencode(
                {
                    "mid": mid,
                    "season_id": season_id,
                    "page_num": page_num,
                    "page_size": 100,
                    "sort_reverse": "false",
                }
            )
            try:
                payload = self._request_json(f"{self.api_base_url}/x/polymer/web-space/seasons_archives_list?{params}")
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
                break
            if payload.get("code") != 0:
                break
            data = payload.get("data")
            if not isinstance(data, dict):
                break
            archives = data.get("archives")
            if not isinstance(archives, list) or not archives:
                break
            for index, archive in enumerate(archives, start=len(children) + 1):
                if not isinstance(archive, dict):
                    continue
                bvid = self._clean_text(archive.get("bvid") or "")
                if not bvid:
                    continue
                children.append(
                    {
                        "bvid": bvid,
                        "cid": str(archive.get("cid") or ""),
                        "index": str(index),
                        "label": f"EP{index}",
                        "title": self._clean_text(archive.get("title") or f"第{index}集"),
                    }
                )
            page = data.get("page")
            if not isinstance(page, dict):
                break
            total = int(page.get("total") or 0)
            page_size = int(page.get("page_size") or 100)
            if len(children) >= total or len(archives) < page_size:
                break
            page_num += 1
        if not children:
            return []
        return [{"title": collection_title or "合集总览", "children": children}]

    def _fetch_playurl(self, *, aid: int, bvid: str, cid: int) -> dict:
        params = self._sign_wbi_params(
            {
                "avid": aid,
                "bvid": bvid,
                "cid": cid,
                "qn": 127,
                "fnval": 4048,
                "fnver": 0,
                "fourk": 1,
            }
        )
        try:
            payload = self._request_json(f"{self.api_base_url}/x/player/wbi/playurl?{params}")
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderUnavailableError("bilibili web playurl request failed") from exc
        if payload.get("code") != 0:
            raise ProviderUnavailableError(f"bilibili web playurl returned code {payload.get('code')}")
        return payload

    def _fetch_progressive_playurl(
        self,
        *,
        aid: int,
        bvid: str,
        cid: int,
        quality_code: int | None,
    ) -> dict:
        params = self._sign_wbi_params(
            {
                "avid": aid,
                "bvid": bvid,
                "cid": cid,
                "qn": quality_code or 80,
                "fnval": 0,
                "fnver": 0,
                "fourk": 1,
            }
        )
        try:
            payload = self._request_json(f"{self.api_base_url}/x/player/wbi/playurl?{params}")
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderUnavailableError("bilibili web progressive playurl request failed") from exc
        if payload.get("code") != 0:
            raise ProviderUnavailableError(f"bilibili web progressive playurl returned code {payload.get('code')}")
        return payload

    def _match_quality_label(
        self,
        selected_quality: object,
        accept_quality: list[object],
        accept_description: list[object],
    ) -> str:
        for index, quality in enumerate(accept_quality):
            if str(quality) == str(selected_quality):
                return str(accept_description[index]) if index < len(accept_description) else str(selected_quality or "")
        return str(selected_quality or "")
