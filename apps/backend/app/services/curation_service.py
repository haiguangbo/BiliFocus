import re
from collections.abc import Callable
from datetime import UTC, datetime

from app.core.config import Settings
from app.providers.base import SearchProvider
from app.providers.factory import SearchProviderFactory
from app.repositories.query_history_repository import QueryHistoryRepository
from app.repositories.sync_job_repository import SyncJobRepository
from app.repositories.video_repository import VideoRepository
from app.schemas.curation import CurationPipelineTrace, CurationRunRequest, CurationRunResponse, PipelineStageTrace
from app.schemas.video import RecommendationReason, VideoDetail, VideoItem
from app.services.bilibili_prompt_templates import BilibiliPromptTemplates
from app.services.crewai_curation_service import CrewAICurationService
from app.services.llm_adapter import BaseLLMAdapter, build_llm_adapter
from app.services.llm_refinement_service import LLMRefinementService


class CurationService:
    CLICKBAIT_PATTERNS = [
        r"震惊",
        r"一定要看",
        r"看完.*哭",
        r"全网最",
        r"居然",
        r"速看",
        r"三分钟",
        r"一分钟",
        r"秒懂",
        r"标题党",
        r"[!！]{2,}",
    ]
    LIVE_CLIP_PATTERNS = ["直播", "切片", "录播", "reaction", "搬运"]
    INTENT_STOPWORDS = {
        "需要",
        "现在",
        "一些",
        "质量",
        "上乘",
        "等等",
        "内容",
        "视频",
        "现在需要",
        "家里",
        "家里的",
        "小朋友",
        "学习",
        "合适",
        "适合",
        "希望",
        "用于",
        "能够",
        "可以",
        "相关",
        "提升",
    }

    def __init__(
        self,
        *,
        settings: Settings,
        provider_factory: SearchProviderFactory,
        video_repository: VideoRepository,
        query_history_repository: QueryHistoryRepository,
        sync_job_repository: SyncJobRepository,
        llm_refinement_service: LLMRefinementService,
        crewai_curation_service: CrewAICurationService,
        llm_adapter: BaseLLMAdapter | None = None,
        prompt_templates: BilibiliPromptTemplates | None = None,
    ) -> None:
        self.settings = settings
        self.provider_factory = provider_factory
        self.video_repository = video_repository
        self.query_history_repository = query_history_repository
        self.sync_job_repository = sync_job_repository
        self.llm_refinement_service = llm_refinement_service
        self.crewai_curation_service = crewai_curation_service
        self.llm_adapter = llm_adapter or build_llm_adapter(settings)
        self.prompt_templates = prompt_templates or BilibiliPromptTemplates()

    def run(
        self,
        payload: CurationRunRequest,
        *,
        job_id: str | None = None,
        progress_callback: Callable[[str, str, str], None] | None = None,
    ) -> CurationRunResponse:
        started_at = datetime.now(UTC)
        job_id = job_id or f"curation_{started_at.strftime('%Y%m%d_%H%M%S')}"
        objective_text = self._compose_objective(payload.objective, payload.extra_requirements)
        rewritten_objective = self._rewrite_objective(payload.objective, payload.extra_requirements)
        job = self.sync_job_repository.create_job(
            job_id=job_id,
            query=payload.objective,
            filter_text=payload.extra_requirements,
            source="agentic-curation",
            status="running",
            started_at=started_at.isoformat(),
        )

        provider = self.provider_factory.resolve("default")
        self._report_progress(progress_callback, "planner", "running", "正在规划关键词")
        keywords, planner_trace = self._recommend_keywords(payload, rewritten_objective)
        self._report_progress(progress_callback, "collector", "running", "正在从 Bilibili 拉取候选视频")
        candidates = self._collect_candidates(provider, keywords, payload.limit_per_keyword)
        self._report_progress(progress_callback, "reviewer", "running", "正在执行硬规则与 AI 审核")
        reviewed, reviewer_trace, classifier_trace = self._review_candidates(
            candidates,
            objective_text,
            rewritten_objective,
            keywords,
            payload.extra_requirements,
        )
        accepted = [item for item, keep in reviewed if keep]
        self._report_progress(progress_callback, "classifier", "running", "正在整理分类与去重结果")
        accepted = self.llm_refinement_service.refine(
            query=payload.objective,
            filter_text=payload.extra_requirements,
            items=accepted,
        )
        accepted = self._dedupe_items(accepted)
        accepted_preview = accepted[: payload.limit_per_keyword]

        saved_count = 0
        skipped_count = 0
        if payload.sync_accepted and accepted_preview:
            self._report_progress(progress_callback, "sync", "running", "正在同步通过审核的视频到本地片库")
            enriched_items = self._enrich_items(provider, accepted_preview)
            saved_count, skipped_count = self.video_repository.upsert_many(enriched_items)

        finished_at = datetime.now(UTC)
        self.query_history_repository.create_entry(
            query=payload.objective,
            filter_text=payload.extra_requirements,
            source="agentic-curation",
            result_count=len(accepted_preview),
            executed_at=finished_at.isoformat(),
        )
        self.sync_job_repository.complete_job(
            job,
            status="completed",
            saved_count=saved_count,
            skipped_count=skipped_count,
            failed_count=max(0, len(candidates) - len(accepted_preview)),
            finished_at=finished_at.isoformat(),
        )
        self.video_repository.db.commit()
        self._report_progress(progress_callback, "completed", "completed", "AI 策展执行完成")

        return CurationRunResponse(
            job_id=job_id,
            status="completed",
            objective=payload.objective,
            recommended_keywords=keywords,
            pipeline_trace=CurationPipelineTrace(
                planner=planner_trace,
                reviewer=reviewer_trace,
                classifier=classifier_trace,
            ),
            reviewed_count=len(candidates),
            accepted_count=len(accepted_preview),
            rejected_count=max(0, len(candidates) - len(accepted_preview)),
            saved_count=saved_count,
            skipped_count=skipped_count,
            accepted_items=[
                item.model_copy(update={"cached": True if payload.sync_accepted else item.cached})
                for item in accepted_preview
            ],
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
        )

    def _compose_objective(self, objective: str, extra_requirements: str | None) -> str:
        parts = [objective.strip()]
        if extra_requirements:
            parts.append(extra_requirements.strip())
        return "；".join(part for part in parts if part)

    def _recommend_keywords(
        self,
        payload: CurationRunRequest,
        rewritten_objective: str,
    ) -> tuple[list[str], PipelineStageTrace]:
        heuristic_keywords = self._heuristic_keywords(rewritten_objective, payload.extra_requirements)
        try:
            crewai_keywords = self.crewai_curation_service.plan_keywords(
                objective=rewritten_objective,
                extra_requirements=payload.extra_requirements,
                max_keywords=payload.max_keywords,
            )
        except Exception:
            crewai_keywords = []
        if crewai_keywords:
            merged = self._merge_keywords(crewai_keywords + heuristic_keywords)[: payload.max_keywords]
            return merged, PipelineStageTrace(
                agent="crewai.keyword_planner",
                status="completed",
                summary=f"CrewAI planner 生成并合并了 {len(merged)} 个关键词",
                outputs=merged,
            )
        if self.settings.llm_refinement_enabled and self.llm_adapter.available:
            try:
                llm_keywords = self._llm_keywords(rewritten_objective, payload.extra_requirements, payload.max_keywords)
            except Exception:
                llm_keywords = []
            if llm_keywords:
                merged = self._merge_keywords(llm_keywords + heuristic_keywords)
                trimmed = merged[: payload.max_keywords]
                return trimmed, PipelineStageTrace(
                    agent=f"{self.settings.effective_llm_provider}.keyword_planner",
                    status="fallback",
                    summary=f"未启用 CrewAI planner，改用 {self.settings.effective_llm_provider} adapter 生成了 {len(trimmed)} 个关键词",
                    outputs=trimmed,
                )
        trimmed = heuristic_keywords[: payload.max_keywords]
        return trimmed, PipelineStageTrace(
            agent="local.keyword_planner",
            status="fallback",
            summary=f"未启用 CrewAI/LLM，使用本地规则生成了 {len(trimmed)} 个关键词",
            outputs=trimmed,
        )

    def _heuristic_keywords(self, objective: str, extra_requirements: str | None) -> list[str]:
        text = f"{objective} {extra_requirements or ''}".lower()
        keywords: list[str] = []

        topic_map = [
            (["ai", "人工智能", "大模型", "llm"], ["ai 架构", "大模型 应用", "ai agent", "llm 工程"]),
            (["架构", "系统设计", "architecture"], ["系统设计", "软件架构", "架构设计", "微服务 架构"]),
            (["综合能力", "软技能", "成长"], ["综合能力 提升", "学习方法", "表达能力", "问题解决"]),
            (["英语", "小学生", "启蒙"], ["小学生 英语", "少儿 英语", "英语 启蒙", "自然拼读"]),
        ]

        for tokens, expansion in topic_map:
            if any(token in text for token in tokens):
                keywords.extend(expansion)

        if not keywords:
            keywords.extend([objective.strip(), f"{objective.strip()} 教程", f"{objective.strip()} 入门"])

        return self._merge_keywords(keywords)

    def _llm_keywords(self, objective: str, extra_requirements: str | None, max_keywords: int) -> list[str]:
        data = self.llm_adapter.generate_json(
            schema_name="keyword_plan",
            schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                    }
                },
                "required": ["keywords"],
            },
            system_prompt=self.prompt_templates.keyword_plan_prompt(f"{objective} {extra_requirements or ''}"),
            user_payload={
                "objective": objective,
                "extra_requirements": extra_requirements or "",
                "max_keywords": max_keywords,
            },
            max_output_tokens=300,
        )
        return self._merge_keywords(data.get("keywords", []))

    def _collect_candidates(self, provider: SearchProvider, keywords: list[str], limit_per_keyword: int) -> list[VideoItem]:
        collected: list[VideoItem] = []
        seen: set[str] = set()
        for keyword in keywords:
            for item in provider.search(keyword)[:limit_per_keyword]:
                if item.bvid in seen:
                    continue
                seen.add(item.bvid)
                category_tags = self._infer_category_tags(item, keyword)
                collected.append(
                    item.model_copy(
                        update={
                            "tags": list(dict.fromkeys([*item.tags, keyword, *category_tags])),
                            "match_reasons": [
                                *item.match_reasons,
                                RecommendationReason(code="curation_accept", message=f"Planner 由关键词 {keyword} 命中"),
                            ],
                        }
                    )
                )
        return collected

    def _review_candidates(
        self,
        items: list[VideoItem],
        objective_text: str,
        rewritten_objective: str,
        keywords: list[str],
        extra_requirements: str | None,
    ) -> tuple[list[tuple[VideoItem, bool]], PipelineStageTrace, PipelineStageTrace]:
        try:
            crewai_keep_map, crewai_reason_map = self.crewai_curation_service.review_candidates(
                objective=rewritten_objective,
                extra_requirements=extra_requirements,
                items=items,
            )
        except Exception:
            crewai_keep_map, crewai_reason_map = {}, {}

        reviewed: list[tuple[VideoItem, bool]] = []
        accepted_for_classification: list[VideoItem] = []
        kept_count = 0
        intent_tokens = self._build_intent_tokens(objective_text, rewritten_objective, keywords)
        for item in items:
            keep, reason = self._passes_hard_rules(item, intent_tokens)
            if keep and crewai_keep_map:
                keep = crewai_keep_map.get(item.bvid, keep)
                reason = crewai_reason_map.get(item.bvid, reason)
            if keep:
                kept_count += 1
            reasons = list(item.match_reasons)
            reasons.append(
                RecommendationReason(
                    code="curation_accept" if keep else "hard_rule_reject",
                    message=f"Reviewer {reason}",
                )
            )
            reviewed_item = item.model_copy(update={"match_reasons": reasons})
            reviewed.append((reviewed_item, keep))
            if keep:
                accepted_for_classification.append(reviewed_item)

        try:
            crewai_category_map = self.crewai_curation_service.classify_candidates(
                objective=rewritten_objective,
                extra_requirements=extra_requirements,
                items=accepted_for_classification,
            )
        except Exception:
            crewai_category_map = {}

        classified_reviewed: list[tuple[VideoItem, bool]] = []
        for item, keep in reviewed:
            category_tags = crewai_category_map.get(item.bvid, [])
            classified_reviewed.append(
                (
                    item.model_copy(
                        update={
                            "tags": list(dict.fromkeys([*item.tags, *category_tags])),
                        }
                    ),
                    keep,
                )
            )

        reviewer_trace = self._build_reviewer_trace(items, kept_count, crewai_keep_map)
        classifier_trace = self._build_classifier_trace(crewai_category_map, kept_count)
        return classified_reviewed, reviewer_trace, classifier_trace

    def _passes_hard_rules(self, item: VideoItem, intent_tokens: list[str]) -> tuple[bool, str]:
        haystack = " ".join([item.title, item.summary or "", " ".join(item.tags)]).lower()

        if item.duration_seconds is not None and item.duration_seconds < 180:
            return False, "时长过短，按硬规则排除短视频"

        if any(re.search(pattern, item.title, flags=re.IGNORECASE) for pattern in self.CLICKBAIT_PATTERNS):
            return False, "标题疑似标题党，按硬规则排除"

        if any(token in haystack for token in self.LIVE_CLIP_PATTERNS):
            return False, "疑似直播切片或搬运内容，按硬规则排除"

        if intent_tokens and not any(token in haystack for token in intent_tokens):
            return False, "与当前学习目标相关性过弱"

        return True, "符合学习目标，且通过基础内容审查"

    def _rewrite_objective(self, objective: str, extra_requirements: str | None) -> str:
        fallback = self._fallback_rewritten_objective(objective, extra_requirements)
        if not (self.settings.llm_refinement_enabled and self.llm_adapter.available):
            return fallback
        try:
            data = self.llm_adapter.generate_json(
                schema_name="curation_objective_rewrite",
                schema={
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "rewritten_objective": {"type": "string"},
                    },
                    "required": ["rewritten_objective"],
                },
                system_prompt=self.prompt_templates.rewrite_objective_prompt(f"{objective} {extra_requirements or ''}"),
                user_payload={
                    "objective": objective,
                    "extra_requirements": extra_requirements or "",
                },
                max_output_tokens=200,
            )
            rewritten = str(data.get("rewritten_objective") or "").strip()
            return rewritten or fallback
        except Exception:
            return fallback

    def _fallback_rewritten_objective(self, objective: str, extra_requirements: str | None) -> str:
        named_entities = self._extract_named_entities(f"{objective} {extra_requirements or ''}")
        intent_terms = self._extract_intent_phrases(objective, extra_requirements)
        parts = [*intent_terms[:4], *named_entities[:4]]
        if not parts:
            return objective.strip()
        return "；".join(dict.fromkeys(parts))

    def _build_intent_tokens(
        self,
        objective_text: str,
        rewritten_objective: str,
        keywords: list[str],
    ) -> list[str]:
        tokens = [
            *self._extract_named_entities(objective_text),
            *self._extract_named_entities(rewritten_objective),
            *self._extract_intent_phrases(objective_text),
            *self._extract_intent_phrases(rewritten_objective),
        ]
        for keyword in keywords:
            tokens.extend(self._keyword_tokens(keyword))
            tokens.append(keyword.strip().lower())
        return self._normalize_intent_tokens(tokens)

    def _extract_named_entities(self, text: str) -> list[str]:
        fragments = re.split(r"[\s,，;；、/|（）()：:\n]+", text.lower())
        named: list[str] = []
        for fragment in fragments:
            token = fragment.strip("“”\"'[]【】")
            if len(token) < 2:
                continue
            if token in self.INTENT_STOPWORDS:
                continue
            if any(stop in token for stop in ["需要", "现在", "质量", "一些"]):
                continue
            if re.fullmatch(r"[a-z]{1,2}", token):
                continue
            named.append(token)
        return self._normalize_intent_tokens(named)

    def _extract_intent_phrases(self, objective: str, extra_requirements: str | None = None) -> list[str]:
        text = f"{objective} {extra_requirements or ''}".lower()
        phrases: list[str] = []
        phrase_rules = [
            (["英语", "英文", "english"], ["英语", "英文版"]),
            (["启蒙", "少儿", "儿童", "小朋友", "幼儿"], ["少儿", "儿童", "启蒙"]),
            (["动画", "动画片", "卡通"], ["动画"]),
            (["小猪佩奇", "peppa"], ["小猪佩奇"]),
            (["布鲁依", "bluey", "布鲁伊"], ["布鲁依", "bluey"]),
            (["自然拼读", "phonics"], ["自然拼读"]),
        ]
        for markers, expansions in phrase_rules:
            if any(marker in text for marker in markers):
                phrases.extend(expansions)
        return self._normalize_intent_tokens(phrases)

    def _keyword_tokens(self, keyword: str) -> list[str]:
        return [
            token.strip()
            for token in re.split(r"[\s,，;；、/|]+", keyword.lower())
            if len(token.strip()) >= 2
        ]

    def _normalize_intent_tokens(self, tokens: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            value = str(token).strip().lower()
            if len(value) < 2:
                continue
            if value in self.INTENT_STOPWORDS:
                continue
            if value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized[:20]

    def _enrich_items(self, provider: SearchProvider, items: list[VideoItem]) -> list[VideoItem | VideoDetail]:
        enriched: list[VideoItem | VideoDetail] = []
        for item in items:
            detail = provider.get_video(item.bvid)
            if detail is None:
                enriched.append(item)
                continue
            merged_tags = list(dict.fromkeys([*item.tags, *detail.tags]))
            enriched.append(
                detail.model_copy(
                    update={
                        "title": item.title or detail.title,
                        "author_name": item.author_name or detail.author_name,
                        "cover_url": item.cover_url or detail.cover_url,
                        "duration_seconds": item.duration_seconds or detail.duration_seconds,
                        "published_at": item.published_at or detail.published_at,
                        "view_count": item.view_count or detail.view_count,
                        "like_count": item.like_count or detail.like_count,
                        "summary": item.summary or detail.summary,
                        "tags": merged_tags,
                        "match_reasons": item.match_reasons,
                        "cached": item.cached,
                    }
                )
            )
        return enriched

    def _dedupe_items(self, items: list[VideoItem]) -> list[VideoItem]:
        deduped: list[VideoItem] = []
        seen: set[str] = set()
        for item in items:
            if item.bvid in seen:
                continue
            seen.add(item.bvid)
            deduped.append(item)
        return deduped

    def _merge_keywords(self, keywords: list[str]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for keyword in keywords:
            normalized = str(keyword).strip()
            if not normalized:
                continue
            lowered = normalized.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            merged.append(normalized)
        return merged

    def _infer_category_tags(self, item: VideoItem, keyword: str) -> list[str]:
        haystack = " ".join([item.title, item.summary or "", " ".join(item.tags), keyword]).lower()
        categories: list[str] = []
        if any(token in haystack for token in ["ai", "人工智能", "llm", "大模型", "agent"]):
            categories.append("AI")
        if any(token in haystack for token in ["架构", "architecture", "系统设计", "后端", "分布式"]):
            categories.append("架构")
        if any(token in haystack for token in ["综合能力", "成长", "表达", "学习方法", "沟通"]):
            categories.append("综合能力")
        if any(token in haystack for token in ["英语", "english", "自然拼读", "启蒙", "小学生"]):
            categories.append("英语提升")
        return categories

    def _build_reviewer_trace(
        self,
        items: list[VideoItem],
        kept_count: int,
        crewai_keep_map: dict[str, bool],
    ) -> PipelineStageTrace:
        rejected_count = max(0, len(items) - kept_count)
        if crewai_keep_map:
            return PipelineStageTrace(
                agent="crewai.content_reviewer",
                status="completed",
                summary="CrewAI reviewer 完成了目标相关性与内容质量审核",
                outputs=[f"保留 {kept_count} 条", f"拒绝 {rejected_count} 条"],
            )
        return PipelineStageTrace(
            agent="local.content_reviewer",
            status="fallback",
            summary="未启用 CrewAI reviewer，使用本地硬规则完成审核",
            outputs=[f"保留 {kept_count} 条", f"拒绝 {rejected_count} 条"],
        )

    def _build_classifier_trace(
        self,
        crewai_category_map: dict[str, list[str]],
        kept_count: int,
    ) -> PipelineStageTrace:
        category_names = sorted({category for categories in crewai_category_map.values() for category in categories})
        if crewai_category_map:
            return PipelineStageTrace(
                agent="crewai.content_classifier",
                status="completed",
                summary="CrewAI classifier 已为通过审核的视频补充学习目录标签",
                outputs=category_names[:6] or [f"已处理 {kept_count} 条通过项"],
            )
        return PipelineStageTrace(
            agent="local.content_classifier",
            status="fallback",
            summary="未启用 CrewAI classifier，使用本地启发式标签",
            outputs=[f"已处理 {kept_count} 条通过项"],
        )

    def _report_progress(
        self,
        callback: Callable[[str, str, str], None] | None,
        stage: str,
        status: str,
        message: str,
    ) -> None:
        if callback is not None:
            callback(stage, status, message)
