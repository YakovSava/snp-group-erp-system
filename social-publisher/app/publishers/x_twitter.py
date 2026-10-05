from oauthlib.oauth1 import Client as OAuth1Client

from ..config import Settings
from ..http_client import new_async_client
from ..schemas import PublishRequest, PublishResult
from .base import SocialPublisher

MEDIA_UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"
TWEET_URL = "https://api.twitter.com/2/tweets"


class XPublisher(SocialPublisher):
    """X (Twitter) API v2. Posting requires OAuth1 user-context signing —
    a bearer/app-only token can't create tweets. Media has no "post by
    URL" option either: it's downloaded here and re-uploaded via the v1.1
    media endpoint, then referenced by id in the v2 tweet body."""

    platform = "x"

    def __init__(self, settings: Settings):
        self._settings = settings
        self._configured = bool(
            settings.x_api_key and settings.x_api_secret and settings.x_access_token and settings.x_access_token_secret
        )
        self._oauth = OAuth1Client(
            settings.x_api_key,
            client_secret=settings.x_api_secret,
            resource_owner_key=settings.x_access_token,
            resource_owner_secret=settings.x_access_token_secret,
        )

    def is_configured(self) -> bool:
        return self._configured

    def _auth_header(self, url: str) -> str:
        _, headers, _ = self._oauth.sign(url, http_method="POST")
        return headers["Authorization"]

    async def publish(self, request: PublishRequest) -> PublishResult:
        text = request.text_for(self.platform)

        async with new_async_client(self._settings, timeout=30.0) as client:
            media_ids = []
            for media_url in request.media_urls:
                media_response = await client.get(media_url)
                media_response.raise_for_status()

                upload_response = await client.post(
                    MEDIA_UPLOAD_URL,
                    headers={"Authorization": self._auth_header(MEDIA_UPLOAD_URL)},
                    files={"media": ("media.jpg", media_response.content, "image/jpeg")},
                )
                upload_payload = upload_response.json()
                if upload_response.status_code >= 400:
                    return PublishResult(platform=self.platform, status="error", detail=str(upload_payload))
                media_ids.append(upload_payload["media_id_string"])

            body = {"text": text}
            if media_ids:
                body["media"] = {"media_ids": media_ids}

            response = await client.post(
                TWEET_URL,
                headers={"Authorization": self._auth_header(TWEET_URL)},
                json=body,
            )

        payload = response.json()
        if response.status_code >= 400:
            return PublishResult(platform=self.platform, status="error", detail=str(payload))

        tweet_id = payload["data"]["id"]
        return PublishResult(
            platform=self.platform, status="success", detail="Sent", external_url=f"https://x.com/i/web/status/{tweet_id}"
        )
