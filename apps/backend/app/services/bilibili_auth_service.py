from app.core.config import Settings
from app.providers.bilibili_auth import BilibiliAuthProvider
from app.repositories.preference_repository import PreferenceRepository
from app.schemas.auth import BilibiliQRCodeCreateResponse, BilibiliQRCodePollResponse


class BilibiliAuthService:
    def __init__(self, *, settings: Settings, preference_repository: PreferenceRepository) -> None:
        self.settings = settings
        self.preference_repository = preference_repository
        self.provider = BilibiliAuthProvider(
            referer=settings.bilibili_web_referer,
            user_agent=settings.bilibili_user_agent,
            timeout_seconds=settings.provider_timeout_seconds,
        )

    def create_qrcode(self) -> BilibiliQRCodeCreateResponse:
        payload = self.provider.generate_qrcode()
        return BilibiliQRCodeCreateResponse(
            qrcode_key=payload["qrcode_key"],
            login_url=payload["login_url"],
            expires_in_seconds=180,
        )

    def poll_qrcode(self, qrcode_key: str) -> BilibiliQRCodePollResponse:
        payload = self.provider.poll_qrcode(qrcode_key=qrcode_key)
        login_code = int(payload["login_code"])
        message = str(payload["message"] or "").strip()
        cookie_string = str(payload["cookie_string"] or "").strip()

        state_map = {
            86101: ("pending", "waiting_scan", message or "二维码已生成，等待扫码"),
            86090: ("pending", "waiting_confirm", message or "已扫码，请在手机上确认登录"),
            86038: ("expired", "expired", message or "二维码已过期，请重新生成"),
            0: ("completed", "confirmed", message or "扫码登录成功，已写入本地 Cookie"),
        }
        status, state, resolved_message = state_map.get(
            login_code,
            ("failed", "failed", message or "扫码登录失败"),
        )

        cookie_configured = False
        if login_code == 0 and cookie_string:
            self.preference_repository.save_bilibili_cookie(cookie_string)
            cookie_configured = True

        return BilibiliQRCodePollResponse(
            status=status,
            state=state,
            message=resolved_message,
            cookie_configured=cookie_configured,
        )
