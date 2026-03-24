import json
import re
from datetime import UTC, datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.video import Video
from app.models.video_metric import VideoMetric
from app.schemas.video import RecommendationReason, VideoDetail, VideoItem


class VideoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_videos(
        self,
        *,
        q: str | None,
        tag: str | None,
        sort: str,
        limit: int,
        offset: int,
    ) -> tuple[list[VideoItem], int]:
        query = self.db.query(Video).options(joinedload(Video.metrics))
        if q:
            groups = self._build_semantic_query_groups(q)
            query = query.filter(
                or_(
                    *[
                        or_(
                            Video.title.ilike(f"%{term}%"),
                            Video.author_name.ilike(f"%{term}%"),
                            Video.summary.ilike(f"%{term}%"),
                            Video.tags_json.ilike(f"%{term}%"),
                            Video.raw_extra_json.ilike(f"%{term}%"),
                        )
                        for term in groups
                    ]
                )
            )
        if tag:
            term = f"%{tag}%"
            query = query.filter(
                or_(
                    Video.tags_json.ilike(f'%"{tag}"%'),
                    Video.raw_extra_json.ilike(term),
                )
            )

        if sort == "views":
            query = query.outerjoin(VideoMetric).order_by(VideoMetric.view_count.desc().nullslast(), Video.id.desc())
        elif sort == "published_at":
            query = query.order_by(Video.published_at.desc().nullslast(), Video.id.desc())
        else:
            query = query.order_by(Video.last_synced_at.desc().nullslast(), Video.id.desc())

        total = query.count()
        rows = query.offset(offset).limit(limit).all()
        return [self._to_item(row) for row in rows], total

    def get_by_bvid(self, bvid: str) -> VideoDetail | None:
        row = (
            self.db.query(Video)
            .options(joinedload(Video.metrics))
            .filter(Video.bvid == bvid)
            .first()
        )
        if not row:
            return None
        return self._to_detail(row)

    def list_video_details(self, *, limit: int, tag: str | None = None) -> list[VideoDetail]:
        query = self.db.query(Video).options(joinedload(Video.metrics))
        if tag:
            query = query.filter(Video.tags_json.ilike(f'%"{tag}"%'))
        rows = (
            query.order_by(Video.last_synced_at.desc().nullslast(), Video.id.desc())
            .limit(limit)
            .all()
        )
        return [self._to_detail(row) for row in rows]

    def upsert_many(self, items: list[VideoItem | VideoDetail]) -> tuple[int, int]:
        saved_count = 0
        skipped_count = 0
        for item in items:
            existing = self.db.query(Video).filter(Video.bvid == item.bvid).first()
            now = datetime.now(UTC).isoformat()
            description = item.description if isinstance(item, VideoDetail) else item.summary
            source_url = item.source_url if isinstance(item, VideoDetail) else f"https://www.bilibili.com/video/{item.bvid}"
            raw_extra = item.raw_extra if isinstance(item, VideoDetail) else {"source": "search-sync", "tags": ",".join(item.tags[:3])}
            raw_extra = self._enrich_raw_extra(raw_extra=raw_extra, item=item)
            if existing:
                current_raw_extra = json.loads(existing.raw_extra_json)
                current_raw_extra.update(raw_extra)
                existing.title = item.title
                existing.author_name = item.author_name
                existing.cover_url = item.cover_url
                existing.published_at = item.published_at.isoformat() if item.published_at else None
                existing.summary = item.summary
                existing.duration_seconds = item.duration_seconds
                existing.tags_json = json.dumps(item.tags, ensure_ascii=False)
                existing.description = description
                existing.source_url = source_url
                existing.sync_status = "synced"
                existing.raw_extra_json = json.dumps(current_raw_extra, ensure_ascii=False)
                existing.last_synced_at = now
                existing.updated_at = now
                self._upsert_metrics(existing, item, now)
                skipped_count += 1
                continue
            row = Video(
                bvid=item.bvid,
                title=item.title,
                author_name=item.author_name,
                cover_url=item.cover_url,
                published_at=item.published_at.isoformat() if item.published_at else None,
                summary=item.summary,
                duration_seconds=item.duration_seconds,
                tags_json=json.dumps(item.tags, ensure_ascii=False),
                description=description,
                source_url=source_url,
                sync_status="synced",
                raw_extra_json=json.dumps(raw_extra, ensure_ascii=False),
                cached=True,
                first_seen_at=now,
                last_synced_at=now,
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)
            self.db.flush()
            self._upsert_metrics(row, item, now)
            saved_count += 1
        return saved_count, skipped_count

    def update_raw_extra(self, bvid: str, updates: dict[str, str]) -> None:
        row = self.db.query(Video).filter(Video.bvid == bvid).first()
        if row is None:
            return
        current = json.loads(row.raw_extra_json)
        current.update(updates)
        row.raw_extra_json = json.dumps(current, ensure_ascii=False)
        row.updated_at = datetime.now(UTC).isoformat()

    def rewrite_metadata(
        self,
        *,
        bvid: str,
        summary: str | None,
        tags: list[str],
        raw_extra_updates: dict[str, str],
    ) -> bool:
        row = self.db.query(Video).filter(Video.bvid == bvid).first()
        if row is None:
            return False
        if summary:
            row.summary = summary
        if tags:
            row.tags_json = json.dumps(tags, ensure_ascii=False)
        current = json.loads(row.raw_extra_json)
        current.update(raw_extra_updates)
        current = self._enrich_raw_extra_from_fields(
            raw_extra=current,
            title=row.title,
            summary=row.summary or "",
            tags=json.loads(row.tags_json),
        )
        row.raw_extra_json = json.dumps(current, ensure_ascii=False)
        row.updated_at = datetime.now(UTC).isoformat()
        return True

    def delete_by_bvid(self, bvid: str) -> bool:
        row = self.db.query(Video).filter(Video.bvid == bvid).first()
        if row is None:
            return False
        self.db.delete(row)
        return True

    def _to_item(self, row: Video) -> VideoItem:
        metrics = row.metrics
        raw_extra = json.loads(row.raw_extra_json)
        return VideoItem(
            bvid=row.bvid,
            title=row.title,
            author_name=row.author_name,
            cover_url=row.cover_url,
            duration_seconds=row.duration_seconds,
            published_at=row.published_at,
            view_count=metrics.view_count if metrics else None,
            like_count=metrics.like_count if metrics else None,
            summary=row.summary,
            tags=json.loads(row.tags_json),
            primary_category=raw_extra.get("primary_category"),
            secondary_category=raw_extra.get("secondary_category"),
            series_key=raw_extra.get("series_key"),
            series_title=raw_extra.get("series_title"),
            playback_position_seconds=self._parse_float(raw_extra.get("playback_position_seconds")),
            playback_progress_percent=self._parse_float(raw_extra.get("playback_progress_percent")),
            playback_last_played_at=raw_extra.get("playback_last_played_at"),
            playback_completed=str(raw_extra.get("playback_completed", "false")).lower() == "true",
            match_reasons=[RecommendationReason(code="cached_result", message="来自本地缓存")],
            cached=row.cached,
        )

    def _to_detail(self, row: Video) -> VideoDetail:
        item = self._to_item(row)
        return VideoDetail(
            **item.model_dump(),
            description=row.description,
            source_url=row.source_url,
            sync_status=row.sync_status,
            last_synced_at=row.last_synced_at,
            raw_extra=json.loads(row.raw_extra_json),
        )

    def _upsert_metrics(self, video: Video, item: VideoItem, captured_at: str) -> None:
        metrics = video.metrics
        if metrics is None:
            metrics = VideoMetric(video_id=video.id, captured_at=captured_at)
            self.db.add(metrics)
            video.metrics = metrics
        metrics.view_count = item.view_count
        metrics.like_count = item.like_count
        metrics.captured_at = captured_at

    def _parse_float(self, value: object) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _enrich_raw_extra(self, *, raw_extra: dict[str, str], item: VideoItem | VideoDetail) -> dict[str, str]:
        return self._enrich_raw_extra_from_fields(
            raw_extra=raw_extra,
            title=item.title,
            summary=item.summary or "",
            tags=item.tags,
        )

    def _enrich_raw_extra_from_fields(
        self,
        *,
        raw_extra: dict[str, str],
        title: str,
        summary: str,
        tags: list[str],
    ) -> dict[str, str]:
        enriched = dict(raw_extra)
        primary_category, secondary_category = self._infer_categories(title=title, summary=summary, tags=tags)
        series_title = self._infer_series_title(title)
        series_key = self._slugify_series_key(series_title)

        if primary_category and not enriched.get("primary_category"):
            enriched["primary_category"] = primary_category
        if secondary_category and not enriched.get("secondary_category"):
            enriched["secondary_category"] = secondary_category
        if series_title and not enriched.get("series_title"):
            enriched["series_title"] = series_title
        if series_key and not enriched.get("series_key"):
            enriched["series_key"] = series_key
        return enriched

    def _infer_categories(self, *, title: str, summary: str, tags: list[str]) -> tuple[str, str]:
        haystack = " ".join([title, summary, " ".join(tags)]).lower()
        if any(token in haystack for token in ["英语", "英文", "启蒙", "自然拼读", "bluey", "布鲁依", "小猪佩奇"]):
            return "英语提升", "少儿英语"
        if any(token in haystack for token in ["ai", "大模型", "llm", "agent", "人工智能"]):
            return "AI", "大模型应用"
        if any(token in haystack for token in ["架构", "后端", "系统设计", "分布式"]):
            return "架构", "后端工程"
        if any(token in haystack for token in ["表达", "沟通", "综合能力", "学习方法"]):
            return "综合能力", "方法训练"
        return "未分类", "待整理"

    def _infer_series_title(self, title: str) -> str:
        title = title.strip()
        normalized = (
            title
            .replace("【", " ")
            .replace("】", " ")
        )
        normalized = json.loads(json.dumps(normalized, ensure_ascii=False))
        for pattern in [
            r"第\s*\d+\s*[季集话]",
            r"(?:ep|episode|e)\s*\d+",
            r"\d+\s*连播",
            r"\d+\s*集",
        ]:
            normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)
        normalized = " ".join(normalized.split()).strip(" -_")
        return normalized[:80] or title[:80]

    def _slugify_series_key(self, title: str) -> str:
        lowered = title.lower().strip()
        lowered = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "-", lowered)
        lowered = re.sub(r"-{2,}", "-", lowered).strip("-")
        return lowered[:96]

    def _build_semantic_query_groups(self, query: str) -> list[str]:
        groups: list[str] = []
        normalized = query.strip()
        if normalized:
            groups.append(normalized)

        for token in re.split(r"[\s,，、;；|/]+", normalized):
            token = token.strip()
            if not token or len(token) < 2:
                continue
            groups.append(token)
            for alias in self._semantic_aliases(token):
                groups.append(alias)

        seen: set[str] = set()
        deduped: list[str] = []
        for entry in groups:
            lowered = entry.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            deduped.append(entry)
        return deduped[:12]

    def _semantic_aliases(self, token: str) -> list[str]:
        lowered = token.lower()
        aliases: list[str] = []
        if any(marker in lowered for marker in ["英语", "英文", "启蒙", "自然拼读", "peppa", "bluey", "布鲁依", "小猪佩奇"]):
            aliases.extend(["英语", "英文", "启蒙", "动画", "字幕"])
        if any(marker in lowered for marker in ["ai", "大模型", "llm", "agent", "人工智能"]):
            aliases.extend(["AI", "大模型", "LLM", "Agent", "系统设计"])
        if any(marker in lowered for marker in ["架构", "后端", "系统设计", "分布式"]):
            aliases.extend(["架构", "后端", "系统设计", "分布式"])
        if any(marker in lowered for marker in ["综合能力", "沟通", "表达", "学习方法"]):
            aliases.extend(["综合能力", "表达", "沟通", "学习方法"])
        if "系列" in token or "合集" in token:
            aliases.extend(["系列", "合集", "连播"])
        return aliases
