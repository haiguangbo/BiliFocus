from pydantic import BaseModel, Field


class BilibiliQRCodeCreateResponse(BaseModel):
    status: str = "pending"
    qrcode_key: str
    login_url: str
    expires_in_seconds: int = Field(default=180, ge=1)


class BilibiliQRCodePollResponse(BaseModel):
    status: str
    state: str
    message: str
    cookie_configured: bool = False
