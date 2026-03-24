import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import build_api_router
from app.core.config import get_settings
from app.core.database import init_db
from app.schemas.health import HealthResponse
from app.services.llm_adapter import build_llm_adapter

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    llm_adapter = build_llm_adapter(settings)
    logger.warning(
        "LLM adapter active: provider=%s adapter=%s configured=%s model=%s",
        settings.effective_llm_provider,
        llm_adapter.__class__.__name__,
        llm_adapter.available,
        settings.effective_llm_model or "<empty>",
    )
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(build_api_router(), prefix=settings.api_prefix)


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
    )
