from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.preference_repository import PreferenceRepository
from app.schemas.preference import PreferenceConfig, PreferenceUpdateResponse
from app.services.preference_service import PreferenceService

router = APIRouter(tags=["preferences"])


def get_preference_service(db: Session = Depends(get_db)) -> PreferenceService:
    repository = PreferenceRepository(db)
    return PreferenceService(repository=repository)


@router.get("/preferences", response_model=PreferenceConfig)
def get_preferences(
    service: PreferenceService = Depends(get_preference_service),
) -> PreferenceConfig:
    return service.get_preferences()


@router.put("/preferences", response_model=PreferenceUpdateResponse)
def update_preferences(
    payload: PreferenceConfig,
    service: PreferenceService = Depends(get_preference_service),
) -> PreferenceUpdateResponse:
    return service.save_preferences(payload)
