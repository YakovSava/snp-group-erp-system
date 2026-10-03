import httpx

from ..config import Settings
from ..schemas import PublishRequest, PublishResult
from .base import SocialPublisher

API_BASE = "https://botapi.max.ru"


class MaxPublisher(SocialPublisher):
    """MAX messenger Bot API (dev.max.ru).

    Deliberately Telegram-Bot-API-shaped: a single /messages endpoint, auth
    via an access_token query param (not a header), attachments passed as
    {type, payload: {url}} rather than Telegram's per-method media fields.
    """

    platform = "max"

    def __init__(self, settings: Settings):
        self._token = settings.max_bot_token
        self._chat_id = settings.max_chat_id

    def is_configured(self) -> bool:
        return bool(self._token and self._chat_id)

    async def publish(self, request: PublishRequest) -> PublishResult:
        text = request.text_for(self.platform)
        body = {
            "text": text,
            "attachments": [{"type": "image", "payload": {"url": url}} for url in request.media_urls],
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/messages",
                params={"access_token": self._token, "chat_id": self._chat_id},
                json=body,
            )

        if response.status_code >= 400:
            return PublishResult(platform=self.platform, status="error", detail=response.text)

        return PublishResult(platform=self.platform, status="success", detail="Sent")
