import httpx

from ..config import Settings
from ..schemas import PublishRequest, PublishResult
from .base import SocialPublisher

GRAPH_BASE = "https://graph.threads.net/v1.0"


class ThreadsPublisher(SocialPublisher):
    """Meta's Threads Graph API — a separate API from Facebook/Instagram's,
    but the same two-step container -> publish shape."""

    platform = "threads"

    def __init__(self, settings: Settings):
        self._user_id = settings.threads_user_id
        self._token = settings.threads_access_token

    def is_configured(self) -> bool:
        return bool(self._user_id and self._token)

    async def publish(self, request: PublishRequest) -> PublishResult:
        text = request.text_for(self.platform)
        data = {"access_token": self._token}
        if request.media_urls:
            data.update({"media_type": "IMAGE", "image_url": request.media_urls[0], "text": text})
        else:
            data.update({"media_type": "TEXT", "text": text})

        async with httpx.AsyncClient(timeout=30.0) as client:
            container = await client.post(f"{GRAPH_BASE}/{self._user_id}/threads", data=data)
            container_payload = container.json()
            if container.status_code >= 400:
                return PublishResult(
                    platform=self.platform, status="error", detail=str(container_payload.get("error", container_payload))
                )

            publish_response = await client.post(
                f"{GRAPH_BASE}/{self._user_id}/threads_publish",
                data={"creation_id": container_payload["id"], "access_token": self._token},
            )

        publish_payload = publish_response.json()
        if publish_response.status_code >= 400:
            return PublishResult(
                platform=self.platform, status="error", detail=str(publish_payload.get("error", publish_payload))
            )

        return PublishResult(platform=self.platform, status="success", detail="Sent", external_url=None)
