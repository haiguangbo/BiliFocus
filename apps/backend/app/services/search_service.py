from datetime import UTC, datetime

from app.core.config import Settings
from app.providers.base import SearchProvider
from app.providers.factory import SearchProviderFactory
from app.repositories.query_history_repository import QueryHistoryRepository
from app.repositories.sync_job_repository import SyncJobRepository
from app.repositories.video_repository import VideoRepository
from app.schemas.search import SearchRequest, SearchResponse, SearchSyncRequest, SearchSyncResponse
from app.schemas.video import VideoDetail, VideoItem
from app.services.filter_service import LightweightFilterService
from app.services.llm_refinement_service import LLMRefinementService


class SearchService:
    def __init__(
        self,
        settings: Settings,
        provider_factory: SearchProviderFactory,
        video_repository: VideoRepository,
        query_history_repository: QueryHistoryRepository,
        sync_job_repository: SyncJobRepository,
        filter_service: LightweightFilterService,
        llm_refinement_service: LLMRefinementService,
    ) -> None:
        self.settings = settings
        self.provider_factory = provider_factory
        self.video_repository = video_repository
        self.query_history_repository = query_history_repository
        self.sync_job_repository = sync_job_repository
        self.filter_service = filter_service
        self.llm_refinement_service = llm_refinement_service

    def _resolve_provider(self, source: str) -> SearchProvider:
        return self.provider_factory.resolve(source)

    def search(self, payload: SearchRequest) -> SearchResponse:
        provider = self._resolve_provider(payload.source)
        items = provider.search(payload.query, payload.filter_text)
        filtered_items = self.filter_service.apply(items, payload.filter_text)
        filtered_items = self.llm_refinement_service.refine(
            query=payload.query,
            filter_text=payload.filter_text,
            items=filtered_items,
        )
        sliced = filtered_items[payload.offset : payload.offset + payload.limit]
        executed_at = datetime.now(UTC).isoformat()
        self.query_history_repository.create_entry(
            query=payload.query,
            filter_text=payload.filter_text,
            source=payload.source,
            result_count=len(filtered_items),
            executed_at=executed_at,
        )
        self.video_repository.db.commit()
        return SearchResponse(
            query=payload.query,
            filter_text=payload.filter_text,
            items=sliced,
            total=len(filtered_items),
            limit=payload.limit,
            offset=payload.offset,
        )

    def sync_search(self, payload: SearchSyncRequest) -> SearchSyncResponse:
        started_at = datetime.now(UTC)
        job_id = f"sync_{started_at.strftime('%Y%m%d_%H%M%S')}"
        job = self.sync_job_repository.create_job(
            job_id=job_id,
            query=payload.query,
            filter_text=payload.filter_text,
            source=payload.source,
            status="running",
            started_at=started_at.isoformat(),
        )
        provider = self._resolve_provider(payload.source)
        items = provider.search(payload.query, payload.filter_text)
        filtered_items = self.filter_service.apply(items, payload.filter_text)
        filtered_items = self.llm_refinement_service.refine(
            query=payload.query,
            filter_text=payload.filter_text,
            items=filtered_items,
        )
        sliced = filtered_items[: payload.limit]
        enriched_items = self._enrich_items(provider, sliced)
        saved_count, skipped_count = self.video_repository.upsert_many(enriched_items)
        finished_at = datetime.now(UTC)
        self.query_history_repository.create_entry(
            query=payload.query,
            filter_text=payload.filter_text,
            source=payload.source,
            result_count=len(sliced),
            executed_at=finished_at.isoformat(),
        )
        self.sync_job_repository.complete_job(
            job,
            status="completed",
            saved_count=saved_count,
            skipped_count=skipped_count,
            failed_count=0,
            finished_at=finished_at.isoformat(),
        )
        self.video_repository.db.commit()
        return SearchSyncResponse(
            job_id=job_id,
            status="completed",
            query=payload.query,
            saved_count=saved_count,
            skipped_count=skipped_count,
            failed_count=0,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
        )

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
