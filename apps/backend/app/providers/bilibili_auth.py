import json
from http.cookiejar import CookieJar
from http.cookies import SimpleCookie
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from app.providers.base import ProviderUnavailableError


class BilibiliAuthProvider:
    PASSPORT_BASE_URL = "https://passport.bilibili.com"

    def __init__(self, *, referer: str, user_agent: str, timeout_seconds: float) -> None:
        self.referer = referer
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.cookie_jar = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))

    def generate_qrcode(self) -> dict[str, str]:
        try:
            payload = self._request_json(f"{self.PASSPORT_BASE_URL}/x/passport-login/web/qrcode/generate")
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderUnavailableError("failed to request bilibili qrcode login session") from exc

        if payload.get("code") != 0:
            raise ProviderUnavailableError(f"bilibili qrcode generate returned code {payload.get('code')}")

        data = payload.get("data")
        if not isinstance(data, dict):
            raise ProviderUnavailableError("bilibili qrcode generate returned invalid payload")

        qrcode_key = str(data.get("qrcode_key") or "").strip()
        login_url = str(data.get("url") or "").strip()
        if not qrcode_key or not login_url:
            raise ProviderUnavailableError("bilibili qrcode generate did not return qrcode payload")

        return {
            "qrcode_key": qrcode_key,
            "login_url": login_url,
        }

    def poll_qrcode(self, *, qrcode_key: str) -> dict[str, object]:
        params = urlencode({"qrcode_key": qrcode_key})
        try:
            payload = self._request_json(f"{self.PASSPORT_BASE_URL}/x/passport-login/web/qrcode/poll?{params}")
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderUnavailableError("failed to poll bilibili qrcode login status") from exc

        if payload.get("code") != 0:
            raise ProviderUnavailableError(f"bilibili qrcode poll returned code {payload.get('code')}")

        data = payload.get("data")
        if not isinstance(data, dict):
            raise ProviderUnavailableError("bilibili qrcode poll returned invalid payload")

        login_code = int(data.get("code") or 0)
        message = str(data.get("message") or payload.get("message") or "").strip()
        login_url = str(data.get("url") or "").strip()

        if login_code == 0 and login_url:
            self._follow_login_redirect(login_url)

        cookie_string = self.cookie_string()
        return {
            "login_code": login_code,
            "message": message,
            "cookie_string": cookie_string,
        }

    def cookie_string(self) -> str:
        parts = [f"{cookie.name}={cookie.value}" for cookie in self.cookie_jar]
        return "; ".join(part for part in parts if part)

    def _follow_login_redirect(self, login_url: str) -> None:
        request = Request(login_url, headers=self._build_headers(accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"))
        try:
            with self.opener.open(request, timeout=self.timeout_seconds) as response:
                response.read()
        except (HTTPError, URLError, TimeoutError):
            # Keep best-effort semantics; cookie jar may already contain the login cookie.
            return

    def _request_json(self, url: str) -> dict:
        request = Request(url, headers=self._build_headers())
        with self.opener.open(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _build_headers(self, accept: str = "application/json") -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Referer": self.referer,
            "Accept": accept,
            "Origin": self._origin_from_url(self.referer),
        }

    def _origin_from_url(self, value: str) -> str:
        if value.startswith("https://"):
            host = value.split("/", 3)[2]
            return f"https://{host}"
        if value.startswith("http://"):
            host = value.split("/", 3)[2]
            return f"http://{host}"
        return "https://www.bilibili.com"
