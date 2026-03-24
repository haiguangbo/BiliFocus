from app.core.config import Settings
from app.schemas.video import RecommendationReason, VideoItem
from app.services.bilibili_prompt_templates import BilibiliPromptTemplates
from app.services.llm_adapter import BaseLLMAdapter, build_llm_adapter


class LLMRefinementService:
    def __init__(
        self,
        settings: Settings,
        llm_adapter: BaseLLMAdapter | None = None,
        prompt_templates: BilibiliPromptTemplates | None = None,
    ) -> None:
        self.settings = settings
        self.llm_adapter = llm_adapter or build_llm_adapter(settings)
        self.prompt_templates = prompt_templates or BilibiliPromptTemplates()

    def refine(self, *, query: str, filter_text: str | None, items: list[VideoItem]) -> list[VideoItem]:
        if not self.settings.llm_refinement_enabled or not self.llm_adapter.available or len(items) < 2:
            return items

        candidate_count = min(len(items), self.settings.llm_refinement_max_candidates)
        candidates = items[:candidate_count]
        try:
            plan = self._request_refinement(query=query, filter_text=filter_text, items=candidates)
        except Exception:
            return items
        keep_bvids = plan.get("keep_bvids", [])
        classifications = plan.get("classifications", [])

        if not keep_bvids:
            return items

        classification_by_bvid = {
            entry.get("bvid"): entry
            for entry in classifications
            if isinstance(entry, dict) and entry.get("bvid")
        }
        item_by_bvid = {item.bvid: item for item in candidates}

        refined: list[VideoItem] = []
        for bvid in keep_bvids:
            item = item_by_bvid.get(bvid)
            if item is None:
                continue
            refined.append(self._apply_classification(item, classification_by_bvid.get(bvid)))

        if not refined:
            return items

        kept_ids = {item.bvid for item in refined}
        tail = [item for item in items[candidate_count:] if item.bvid not in kept_ids]
        return [*refined, *tail]

    def _request_refinement(self, *, query: str, filter_text: str | None, items: list[VideoItem]) -> dict:
        review_context = f"{query} {filter_text or ''}".strip()
        return self.llm_adapter.generate_json(
            schema_name="video_refinement",
            schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "keep_bvids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "classifications": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "bvid": {"type": "string"},
                                "categories": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "reason": {"type": "string"},
                            },
                            "required": ["bvid", "categories", "reason"],
                        },
                    },
                },
                "required": ["keep_bvids", "classifications"],
            },
            system_prompt=(
                "You refine Bilibili video search results for a local-first learning curation tool. "
                "Keep the most relevant items, remove obvious duplicates or weak matches, "
                "assign up to two short category labels per kept item, and return concise reasons. "
                f"{self.prompt_templates.reviewer_guidance(review_context)}"
            ),
            user_payload={
                "query": query,
                "filter_text": filter_text or "",
                "candidates": [
                    {
                        "bvid": item.bvid,
                        "title": item.title,
                        "author_name": item.author_name,
                        "summary": item.summary or "",
                        "tags": item.tags,
                        "view_count": item.view_count,
                        "like_count": item.like_count,
                    }
                    for item in items
                ],
            },
            max_output_tokens=800,
        )

    def _apply_classification(self, item: VideoItem, classification: dict | None) -> VideoItem:
        if not classification:
            return item

        categories = [
            str(category).strip()
            for category in classification.get("categories", [])
            if str(category).strip()
        ][:2]
        reason = str(classification.get("reason") or "").strip()
        tags = list(dict.fromkeys([*item.tags, *categories]))
        reasons = list(item.match_reasons)
        if reason:
            reasons.append(RecommendationReason(code="llm_refined", message=reason))
        return item.model_copy(update={"tags": tags, "match_reasons": reasons})
