import httpx

from ..config import Settings
from ..schemas import PublishRequest, PublishResult
from .base import SocialPublisher

GRAPH_BASE = "https://graph.facebook.com/v21.0"


class InstagramPublisher(SocialPublisher):
    """Meta Graph API, two-step container flow via the linked IG Business
    Account. Instagram has no text-only post type — an image is required."""

    platform = "instagram"

    def __init__(self, settings: Settings):
        self._ig_user_id = settings.instagram_business_account_id
        self._token = settings.instagram_access_token

    def is_configured(self) -> bool:
        return bool(self._ig_user_id and self._token)

    async def publish(self, request: PublishRequest) -> PublishResult:
        if not request.media_urls:
            return PublishResult(
                platform=self.platform,
                status="error",
                detail="Instagram requires at least one image; text-only posts aren't supported.",
            )

        text = request.text_for(self.platform)

        async with httpx.AsyncClient(timeout=30.0) as client:
            container = await client.post(
                f"{GRAPH_BASE}/{self._ig_user_id}/media",
                data={"image_url": request.media_urls[0], "caption": text, "access_token": self._token},
            )
            container_payload = container.json()
            if container.status_code >= 400:
                return PublishResult(
                    platform=self.platform, status="error", detail=str(container_payload.get("error", container_payload))
                )

            publish_response = await client.post(
                f"{GRAPH_BASE}/{self._ig_user_id}/media_publish",
                data={"creation_id": container_payload["id"], "access_token": self._token},
            )

        publish_payload = publish_response.json()
        if publish_response.status_code >= 400:
            return PublishResult(
                platform=self.platform, status="error", detail=str(publish_payload.get("error", publish_payload))
            )

        return PublishResult(platform=self.platform, status="success", detail="Sent", external_url=None)
