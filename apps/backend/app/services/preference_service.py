from app.repositories.preference_repository import PreferenceRepository
from app.schemas.preference import PreferenceConfig, PreferenceUpdateResponse


class PreferenceService:
    def __init__(self, repository: PreferenceRepository) -> None:
        self.repository = repository

    def get_preferences(self) -> PreferenceConfig:
        return self.repository.get_or_create()

    def save_preferences(self, payload: PreferenceConfig) -> PreferenceUpdateResponse:
        return self.repository.save(payload)
