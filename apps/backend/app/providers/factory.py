from app.core.config import Settings
from app.providers.base import SearchProvider
from app.providers.bilibili_web import BilibiliWebSearchProvider


class SearchProviderFactory:
    def __init__(self, settings: Settings, *, bilibili_cookie: str = "") -> None:
        self.settings = settings
        self.bilibili_cookie = bilibili_cookie

    def resolve(self, source: str) -> SearchProvider:
        del source
        return BilibiliWebSearchProvider(
            api_base_url=self.settings.bilibili_api_base_url,
            referer=self.settings.bilibili_web_referer,
            user_agent=self.settings.bilibili_user_agent,
            timeout_seconds=self.settings.provider_timeout_seconds,
            page_size=self.settings.real_provider_page_size,
            cookie=self.bilibili_cookie,
        )
