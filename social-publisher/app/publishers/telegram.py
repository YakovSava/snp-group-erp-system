import httpx

from ..config import Settings
from ..schemas import PublishRequest, PublishResult
from .base import SocialPublisher

API_BASE = "https://api.telegram.org"


class TelegramPublisher(SocialPublisher):
    platform = "telegram"

    def __init__(self, settings: Settings):
        self._token = settings.telegram_bot_token
        self._chat_id = settings.telegram_chat_id

    def is_configured(self) -> bool:
        return bool(self._token and self._chat_id)

    async def publish(self, request: PublishRequest) -> PublishResult:
        text = request.text_for(self.platform)
        base = f"{API_BASE}/bot{self._token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            if not request.media_urls:
                response = await client.post(
                    f"{base}/sendMessage",
                    json={"chat_id": self._chat_id, "text": text},
                )
            elif len(request.media_urls) == 1:
                response = await client.post(
                    f"{base}/sendPhoto",
                    json={"chat_id": self._chat_id, "photo": request.media_urls[0], "caption": text},
                )
            else:
                media = [
                    {"type": "photo", "media": url, **({"caption": text} if index == 0 else {})}
                    for index, url in enumerate(request.media_urls)
                ]
                response = await client.post(
                    f"{base}/sendMediaGroup",
                    json={"chat_id": self._chat_id, "media": media},
                )

        payload = response.json()
        if not payload.get("ok"):
            return PublishResult(platform=self.platform, status="error", detail=str(payload.get("description")))

        message = payload["result"][0] if isinstance(payload["result"], list) else payload["result"]
        message_id = message.get("message_id")
        return PublishResult(
            platform=self.platform,
            status="success",
            detail="Sent",
            external_url=f"https://t.me/c/{self._chat_id.lstrip('-')}/{message_id}" if message_id else None,
        )
