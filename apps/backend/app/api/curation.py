from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.curation_jobs import job_store, start_curation_job
from app.core.database import SessionLocal, get_db
from app.providers.base import ProviderUnavailableError
from app.providers.factory import SearchProviderFactory
from app.repositories.preference_repository import PreferenceRepository
from app.repositories.query_history_repository import QueryHistoryRepository
from app.repositories.sync_job_repository import SyncJobRepository
from app.repositories.video_repository import VideoRepository
from app.schemas.curation import CurationJobCreateResponse, CurationJobStatusResponse, CurationRunRequest, CurationRunResponse
from app.services.crewai_curation_service import CrewAICurationService
from app.services.curation_service import CurationService
from app.services.llm_refinement_service import LLMRefinementService

router = APIRouter(tags=["curation"])


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def get_curation_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CurationService:
    preferences = PreferenceRepository(db).get_or_create()
    provider_factory = SearchProviderFactory(settings, bilibili_cookie=preferences.bilibili_cookie)
    return CurationService(
        settings=settings,
        provider_factory=provider_factory,
        video_repository=VideoRepository(db),
        query_history_repository=QueryHistoryRepository(db),
        sync_job_repository=SyncJobRepository(db),
        llm_refinement_service=LLMRefinementService(settings),
        crewai_curation_service=CrewAICurationService(settings),
    )


def build_curation_service(settings: Settings) -> CurationService:
    db = SessionLocal()
    preferences = PreferenceRepository(db).get_or_create()
    provider_factory = SearchProviderFactory(settings, bilibili_cookie=preferences.bilibili_cookie)
    return CurationService(
        settings=settings,
        provider_factory=provider_factory,
        video_repository=VideoRepository(db),
        query_history_repository=QueryHistoryRepository(db),
        sync_job_repository=SyncJobRepository(db),
        llm_refinement_service=LLMRefinementService(settings),
        crewai_curation_service=CrewAICurationService(settings),
    )


@router.post("/curation/run", response_model=CurationRunResponse)
def run_curation(
    payload: CurationRunRequest,
    service: CurationService = Depends(get_curation_service),
) -> CurationRunResponse:
    try:
        return service.run(payload)
    except ProviderUnavailableError:
        return error_response(503, "provider_unavailable", "real Bilibili provider is unavailable")
    except Exception:
        return error_response(500, "curation_failed", "failed to run curation pipeline")


@router.post("/curation/jobs", response_model=CurationJobCreateResponse)
def create_curation_job(
    payload: CurationRunRequest,
    settings: Settings = Depends(get_settings),
) -> CurationJobCreateResponse:
    job_id = f"curation_{payload.objective[:8]}_{payload.max_keywords}_{payload.limit_per_keyword}".replace(" ", "_")
    job_id = f"{job_id}_{len(job_store._jobs) + 1}"

    def runner(job_payload: CurationRunRequest, active_job_id: str) -> CurationRunResponse:
        service = build_curation_service(settings)
        try:
            return service.run(
                job_payload,
                job_id=active_job_id,
                progress_callback=lambda stage, status, message: job_store.update(
                    active_job_id,
                    status=status,
                    stage=stage,
                    progress_message=message,
                ),
            )
        finally:
            service.video_repository.db.close()

    return start_curation_job(job_id=job_id, payload=payload, runner=runner)


@router.get("/curation/jobs/{job_id}", response_model=CurationJobStatusResponse)
def get_curation_job(job_id: str) -> CurationJobStatusResponse:
    snapshot = job_store.get(job_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="curation job not found")
    return snapshot
