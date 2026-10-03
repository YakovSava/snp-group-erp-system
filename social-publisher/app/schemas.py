from typing import Literal

from pydantic import BaseModel, Field


class PublishRequest(BaseModel):
    text: str = ""
    platform_text: dict[str, str] = Field(default_factory=dict)
    media_urls: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=lambda: ["all"])

    def text_for(self, platform: str) -> str:
        return self.platform_text.get(platform) or self.text


class PublishResult(BaseModel):
    platform: str
    status: Literal["success", "error", "skipped_unconfigured"]
    detail: str = ""
    external_url: str | None = None


class PublishResponse(BaseModel):
    results: list[PublishResult]
