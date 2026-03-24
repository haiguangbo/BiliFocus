from __future__ import annotations

from datetime import UTC, datetime

from app.core.config import Settings
from app.repositories.video_repository import VideoRepository
from app.schemas.video import VideoDetail, VideoMetadataRewriteResponse
from app.services.bilibili_prompt_templates import BilibiliPromptTemplates
from app.services.llm_adapter import BaseLLMAdapter, build_llm_adapter


class MetadataRewriteService:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: VideoRepository,
        llm_adapter: BaseLLMAdapter | None = None,
        prompt_templates: BilibiliPromptTemplates | None = None,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.llm_adapter = llm_adapter or build_llm_adapter(settings)
        self.prompt_templates = prompt_templates or BilibiliPromptTemplates()

    def rewrite_library_metadata(self, *, limit: int, tag: str | None = None) -> VideoMetadataRewriteResponse:
        started_at = datetime.now(UTC)
        job_id = f"rewrite_metadata_{started_at.strftime('%Y%m%d_%H%M%S')}"
        items = self.repository.list_video_details(limit=limit, tag=tag)

        rewritten_count = 0
        skipped_count = 0
        updated_bvids: list[str] = []
        for item in items:
            plan = self._rewrite_item(item)
            if plan is None:
                skipped_count += 1
                continue
            updated = self.repository.rewrite_metadata(
                bvid=item.bvid,
                summary=plan["summary"],
                tags=plan["tags"],
                raw_extra_updates=plan["raw_extra_updates"],
            )
            if updated:
                rewritten_count += 1
                updated_bvids.append(item.bvid)
            else:
                skipped_count += 1

        self.repository.db.commit()
        finished_at = datetime.now(UTC)
        return VideoMetadataRewriteResponse(
            job_id=job_id,
            status="completed",
            rewritten_count=rewritten_count,
            skipped_count=skipped_count,
            updated_bvids=updated_bvids,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
        )

    def _rewrite_item(self, item: VideoDetail) -> dict[str, str | list[str] | dict[str, str]] | None:
        fallback = self._fallback_plan(item)
        if not self.llm_adapter.available:
            return fallback

        try:
            data = self.llm_adapter.generate_json(
                schema_name="video_metadata_rewrite",
                schema={
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "summary": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "audience": {"type": "string"},
                        "focus": {"type": "array", "items": {"type": "string"}},
                        "quality_notes": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["summary", "tags", "audience", "focus", "quality_notes"],
                },
                system_prompt=self.prompt_templates.metadata_rewrite_prompt(
                    " ".join([item.title, item.summary or "", item.description or "", " ".join(item.tags)])
                ),
                user_payload={
                    "bvid": item.bvid,
                    "title": item.title,
                    "author_name": item.author_name,
                    "summary": item.summary or "",
                    "description": item.description or "",
                    "tags": item.tags,
                    "raw_extra": item.raw_extra,
                },
                max_output_tokens=500,
            )
            tags = self.prompt_templates.fallback_metadata_tags(
                item.title,
                str(data.get("summary") or item.summary or ""),
                [str(tag) for tag in data.get("tags", [])],
            )
            return {
                "summary": str(data.get("summary") or item.summary or "").strip(),
                "tags": tags,
                "raw_extra_updates": {
                    "structured_summary": str(data.get("summary") or "").strip(),
                    "rewrite_audience": str(data.get("audience") or "").strip(),
                    "rewrite_focus": ",".join(str(entry).strip() for entry in data.get("focus", []) if str(entry).strip()),
                    "rewrite_quality_notes": ",".join(
                        str(entry).strip() for entry in data.get("quality_notes", []) if str(entry).strip()
                    ),
                    "rewrite_last_run_at": datetime.now(UTC).isoformat(),
                },
            }
        except Exception:
            return fallback

    def _fallback_plan(self, item: VideoDetail) -> dict[str, str | list[str] | dict[str, str]]:
        tags = self.prompt_templates.fallback_metadata_tags(item.title, item.summary or "", item.tags)
        summary = (item.summary or item.description or item.title).strip()
        if len(summary) > 120:
            summary = f"{summary[:117]}..."
        return {
            "summary": summary,
            "tags": tags,
            "raw_extra_updates": {
                "structured_summary": summary,
                "rewrite_audience": self._infer_audience(item),
                "rewrite_focus": ",".join(tags[:3]),
                "rewrite_quality_notes": self._infer_quality_notes(item),
                "rewrite_last_run_at": datetime.now(UTC).isoformat(),
            },
        }

    def _infer_audience(self, item: VideoDetail) -> str:
        haystack = " ".join([item.title, item.summary or "", item.description or "", " ".join(item.tags)]).lower()
        if any(token in haystack for token in ["儿童", "少儿", "幼儿", "启蒙", "小猪佩奇", "bluey", "布鲁依"]):
            return "少儿学习者"
        if any(token in haystack for token in ["ai", "大模型", "架构", "系统设计", "后端"]):
            return "开发者"
        return "通用学习者"

    def _infer_quality_notes(self, item: VideoDetail) -> str:
        notes: list[str] = []
        duration_seconds = getattr(item, "duration_seconds", None)
        if duration_seconds and duration_seconds >= 600:
            notes.append("时长较完整")
        if "中英字幕" in (item.summary or "") or "字幕" in item.title:
            notes.append("字幕信息明确")
        if any(token in item.title for token in ["合集", "连播", "英文版"]):
            notes.append("适合连续学习")
        return "，".join(notes[:3])
