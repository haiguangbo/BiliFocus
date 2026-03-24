from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.providers.base import ProviderUnavailableError
from app.repositories.preference_repository import PreferenceRepository
from app.schemas.auth import BilibiliQRCodeCreateResponse, BilibiliQRCodePollResponse
from app.services.bilibili_auth_service import BilibiliAuthService

router = APIRouter(tags=["auth"])


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def get_bilibili_auth_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BilibiliAuthService:
    return BilibiliAuthService(
        settings=settings,
        preference_repository=PreferenceRepository(db),
    )


@router.get("/auth/bilibili/qrcode", response_model=BilibiliQRCodeCreateResponse)
def create_bilibili_qrcode(
    service: BilibiliAuthService = Depends(get_bilibili_auth_service),
) -> BilibiliQRCodeCreateResponse:
    try:
        return service.create_qrcode()
    except ProviderUnavailableError as exc:
        return error_response(503, "provider_unavailable", str(exc) or "bilibili auth provider is unavailable")
    except Exception:
        return error_response(500, "auth_failed", "failed to create bilibili qrcode login session")


@router.get("/auth/bilibili/qrcode/poll", response_model=BilibiliQRCodePollResponse)
def poll_bilibili_qrcode(
    qrcode_key: str = Query(min_length=1),
    service: BilibiliAuthService = Depends(get_bilibili_auth_service),
) -> BilibiliQRCodePollResponse:
    try:
        return service.poll_qrcode(qrcode_key)
    except ProviderUnavailableError as exc:
        return error_response(503, "provider_unavailable", str(exc) or "bilibili auth provider is unavailable")
    except Exception:
        return error_response(500, "auth_failed", "failed to poll bilibili qrcode login session")
