import httpx

from ..config import Settings
from ..schemas import PublishRequest, PublishResult
from .base import SocialPublisher

API_BASE = "https://api.vk.com/method"
API_VERSION = "5.199"


class VkPublisher(SocialPublisher):
    """VK API. VK has no "post an image by URL" option — a photo has to be
    downloaded here and re-uploaded through VK's own upload-server dance
    (getWallUploadServer -> upload -> saveWallPhoto) before wall.post can
    reference it."""

    platform = "vk"

    def __init__(self, settings: Settings):
        self._token = settings.vk_access_token
        self._group_id = settings.vk_group_id

    def is_configured(self) -> bool:
        return bool(self._token and self._group_id)

    async def _upload_photo(self, client: httpx.AsyncClient, media_url: str) -> str:
        upload_server = await client.get(
            f"{API_BASE}/photos.getWallUploadServer",
            params={"group_id": self._group_id, "access_token": self._token, "v": API_VERSION},
        )
        upload_url = upload_server.json()["response"]["upload_url"]

        media_response = await client.get(media_url)
        media_response.raise_for_status()

        upload_result = await client.post(
            upload_url,
            files={"photo": ("photo.jpg", media_response.content, "image/jpeg")},
        )
        uploaded = upload_result.json()

        saved = await client.post(
            f"{API_BASE}/photos.saveWallPhoto",
            data={
                "group_id": self._group_id,
                "photo": uploaded["photo"],
                "server": uploaded["server"],
                "hash": uploaded["hash"],
                "access_token": self._token,
                "v": API_VERSION,
            },
        )
        photo = saved.json()["response"][0]
        return f"photo{photo['owner_id']}_{photo['id']}"

    async def publish(self, request: PublishRequest) -> PublishResult:
        text = request.text_for(self.platform)

        async with httpx.AsyncClient(timeout=30.0) as client:
            attachments = [await self._upload_photo(client, url) for url in request.media_urls]

            response = await client.post(
                f"{API_BASE}/wall.post",
                data={
                    "owner_id": f"-{self._group_id}",
                    "message": text,
                    "attachments": ",".join(attachments),
                    "access_token": self._token,
                    "v": API_VERSION,
                },
            )

        payload = response.json()
        if "error" in payload:
            return PublishResult(platform=self.platform, status="error", detail=str(payload["error"]))

        post_id = payload["response"]["post_id"]
        return PublishResult(
            platform=self.platform,
            status="success",
            detail="Sent",
            external_url=f"https://vk.com/wall-{self._group_id}_{post_id}",
        )
