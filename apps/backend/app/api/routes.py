from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.curation import router as curation_router
from app.api.preferences import router as preferences_router
from app.api.search import router as search_router
from app.api.videos import router as videos_router


def build_api_router() -> APIRouter:
    router = APIRouter()
    router.include_router(auth_router)
    router.include_router(search_router)
    router.include_router(curation_router)
    router.include_router(videos_router)
    router.include_router(preferences_router)
    return router
