from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.preference import UserPreference
from app.schemas.preference import PreferenceConfig, PreferenceUpdateResponse


def normalize_default_source(value: str) -> str:
    del value
    return "default"


class PreferenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create(self) -> PreferenceConfig:
        row = self.db.query(UserPreference).filter(UserPreference.singleton_key == "default").first()
        if row is None:
            now = datetime.now(UTC).isoformat()
            row = UserPreference(
                singleton_key="default",
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
        return self._to_config(row)

    def save(self, payload: PreferenceConfig) -> PreferenceUpdateResponse:
        row = self.db.query(UserPreference).filter(UserPreference.singleton_key == "default").first()
        if row is None:
            now = datetime.now(UTC).isoformat()
            row = UserPreference(singleton_key="default", created_at=now, updated_at=now)
            self.db.add(row)
        row.default_search_limit = payload.default_search_limit
        row.default_source = normalize_default_source(payload.default_source)
        row.default_filter_text = payload.default_filter_text
        row.bilibili_cookie = payload.bilibili_cookie
        row.download_output_dir = payload.download_output_dir
        row.theme = payload.theme
        row.language = payload.language
        row.library_sort = payload.library_sort
        row.hide_watched_placeholder = payload.hide_watched_placeholder
        row.updated_at = datetime.now(UTC).isoformat()
        self.db.commit()
        self.db.refresh(row)
        return self._to_update_schema(row)

    def save_bilibili_cookie(self, cookie: str) -> None:
        row = self.db.query(UserPreference).filter(UserPreference.singleton_key == "default").first()
        if row is None:
            now = datetime.now(UTC).isoformat()
            row = UserPreference(singleton_key="default", created_at=now, updated_at=now)
            self.db.add(row)
        row.bilibili_cookie = cookie
        row.updated_at = datetime.now(UTC).isoformat()
        self.db.commit()

    def _to_config(self, row: UserPreference) -> PreferenceConfig:
        return PreferenceConfig(
            default_search_limit=row.default_search_limit,
            default_source=normalize_default_source(row.default_source),
            default_filter_text=row.default_filter_text,
            bilibili_cookie=row.bilibili_cookie,
            download_output_dir=row.download_output_dir,
            theme=row.theme,
            language=row.language,
            library_sort=row.library_sort,
            hide_watched_placeholder=row.hide_watched_placeholder,
        )

    def _to_update_schema(self, row: UserPreference) -> PreferenceUpdateResponse:
        updated_at = datetime.fromisoformat(row.updated_at) if row.updated_at else None
        return PreferenceUpdateResponse(
            default_search_limit=row.default_search_limit,
            default_source=normalize_default_source(row.default_source),
            default_filter_text=row.default_filter_text,
            bilibili_cookie=row.bilibili_cookie,
            download_output_dir=row.download_output_dir,
            theme=row.theme,
            language=row.language,
            library_sort=row.library_sort,
            hide_watched_placeholder=row.hide_watched_placeholder,
            updated_at=updated_at,
        )
