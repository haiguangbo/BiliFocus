from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_name: str = "bilifocus-backend"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./data/bilifocus.db"
    cors_allow_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://frontend:3000"
    default_search_limit: int = 20
    bilibili_api_base_url: str = "https://api.bilibili.com"
    bilibili_web_referer: str = "https://www.bilibili.com/"
    bilibili_user_agent: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    provider_timeout_seconds: float = 8.0
    real_provider_page_size: int = 20
    llm_refinement_enabled: bool = False
    llm_refinement_max_candidates: int = 12
    llm_refinement_timeout_seconds: float = 20.0
    llm_provider: str = "volcengine"
    llm_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_reasoning_effort: str = "low"
    openai_api_key: str = ""
    openai_model: str = "gpt-5-mini"
    openai_reasoning_effort: str = "low"
    crewai_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_path(self) -> Path:
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix):
            raw_path = Path(self.database_url[len(prefix) :])
            if raw_path.is_absolute():
                return raw_path
            return (PROJECT_ROOT / raw_path).resolve()
        raise ValueError("database_url must use sqlite:/// for the MVP")

    @property
    def resolved_database_url(self) -> str:
        return f"sqlite:///{self.database_path}"

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_allow_origins.split(",") if item.strip()]

    @property
    def effective_llm_provider(self) -> str:
        return self.llm_provider.strip().lower() or "volcengine"

    @property
    def effective_llm_base_url(self) -> str:
        base_url = self.llm_base_url.strip()
        if base_url:
            return base_url
        if self.effective_llm_provider == "openai":
            return "https://api.openai.com/v1"
        return "https://ark.cn-beijing.volces.com/api/v3"

    @property
    def effective_llm_api_key(self) -> str:
        return self.llm_api_key.strip() or self.openai_api_key.strip()

    @property
    def effective_llm_model(self) -> str:
        return self.llm_model.strip() or self.openai_model.strip()

    @property
    def effective_llm_reasoning_effort(self) -> str:
        return self.llm_reasoning_effort.strip() or self.openai_reasoning_effort.strip()

    @property
    def llm_adapter_configured(self) -> bool:
        return bool(self.effective_llm_api_key and self.effective_llm_model)


@lru_cache
def get_settings() -> Settings:
    return Settings()
