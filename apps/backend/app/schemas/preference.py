from datetime import datetime

from pydantic import BaseModel, Field


class PreferenceConfig(BaseModel):
    default_search_limit: int = Field(default=20, ge=1, le=50)
    default_source: str = "default"
    default_filter_text: str = ""
    bilibili_cookie: str = ""
    download_output_dir: str = "./data/downloads"
    theme: str = "system"
    language: str = "zh-CN"
    library_sort: str = "recent"
    hide_watched_placeholder: bool = False


class PreferenceUpdateResponse(PreferenceConfig):
    updated_at: datetime | None = None
