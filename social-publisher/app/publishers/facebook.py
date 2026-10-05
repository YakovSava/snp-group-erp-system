from ..config import Settings
from ..http_client import new_async_client
from ..schemas import PublishRequest, PublishResult
from .base import SocialPublisher

GRAPH_BASE = "https://graph.facebook.com/v21.0"


class FacebookPublisher(SocialPublisher):
    """Meta Graph API. Posts to a Page's feed (personal profiles aren't
    postable via the Graph API, only Pages)."""

    platform = "facebook"

    def __init__(self, settings: Settings):
        self._settings = settings
        self._page_id = settings.facebook_page_id
        self._token = settings.facebook_page_access_token

    def is_configured(self) -> bool:
        return bool(self._page_id and self._token)

    async def publish(self, request: PublishRequest) -> PublishResult:
        text = request.text_for(self.platform)

        async with new_async_client(self._settings, timeout=30.0) as client:
            if request.media_urls:
                response = await client.post(
                    f"{GRAPH_BASE}/{self._page_id}/photos",
                    data={"url": request.media_urls[0], "caption": text, "access_token": self._token},
                )
            else:
                response = await client.post(
                    f"{GRAPH_BASE}/{self._page_id}/feed",
                    data={"message": text, "access_token": self._token},
                )

        payload = response.json()
        if response.status_code >= 400:
            return PublishResult(platform=self.platform, status="error", detail=str(payload.get("error", payload)))

        post_id = payload.get("post_id") or payload.get("id")
        return PublishResult(
            platform=self.platform,
            status="success",
            detail="Sent",
            external_url=f"https://www.facebook.com/{post_id}" if post_id else None,
        )
