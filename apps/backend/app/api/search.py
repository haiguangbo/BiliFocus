from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.providers.base import ProviderUnavailableError
from app.providers.factory import SearchProviderFactory
from app.repositories.preference_repository import PreferenceRepository
from app.repositories.query_history_repository import QueryHistoryRepository
from app.repositories.sync_job_repository import SyncJobRepository
from app.repositories.video_repository import VideoRepository
from app.schemas.search import SearchRequest, SearchResponse, SearchSyncRequest, SearchSyncResponse
from app.services.filter_service import LightweightFilterService
from app.services.llm_refinement_service import LLMRefinementService
from app.services.search_service import SearchService

router = APIRouter(tags=["search"])


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def get_search_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SearchService:
    repository = VideoRepository(db)
    preference_repository = PreferenceRepository(db)
    preferences = preference_repository.get_or_create()
    query_history_repository = QueryHistoryRepository(db)
    sync_job_repository = SyncJobRepository(db)
    provider_factory = SearchProviderFactory(settings, bilibili_cookie=preferences.bilibili_cookie)
    filter_service = LightweightFilterService()
    llm_refinement_service = LLMRefinementService(settings)
    return SearchService(
        settings=settings,
        provider_factory=provider_factory,
        video_repository=repository,
        query_history_repository=query_history_repository,
        sync_job_repository=sync_job_repository,
        filter_service=filter_service,
        llm_refinement_service=llm_refinement_service,
    )


@router.post("/search", response_model=SearchResponse)
def search_videos(
    payload: SearchRequest,
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    try:
        return service.search(payload)
    except ProviderUnavailableError as exc:
        return error_response(503, "provider_unavailable", str(exc) or "real Bilibili provider is unavailable")
    except Exception:
        return error_response(500, "search_failed", "failed to search videos")


@router.post("/sync/search", response_model=SearchSyncResponse)
def sync_search_results(
    payload: SearchSyncRequest,
    service: SearchService = Depends(get_search_service),
) -> SearchSyncResponse:
    try:
        return service.sync_search(payload)
    except ProviderUnavailableError as exc:
        return error_response(503, "provider_unavailable", str(exc) or "real Bilibili provider is unavailable")
    except Exception:
        return error_response(500, "sync_failed", "failed to sync search results")
