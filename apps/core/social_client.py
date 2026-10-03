"""Thin client for the social-publisher microservice.

social-publisher is a separate service/deployment (see social-publisher/)
reached over plain HTTP with a shared service token — never exposed to the
browser; Django is the only caller.
"""
from urllib.parse import urljoin

import httpx
from django.conf import settings

DEFAULT_TIMEOUT = 60.0


def _headers():
    return {"X-Service-Token": settings.SOCIAL_PUBLISHER_SERVICE_TOKEN}


def publish_to_all(post) -> list[dict]:
    """Sends `post` to every configured social network at once.

    Per-platform text falls back to post.text when a platform-specific
    field is blank; platforms with no credentials configured on the
    social-publisher side come back with status "skipped_unconfigured"
    rather than being omitted or failing the whole call.
    """
    media_urls = [urljoin(settings.SITE_BASE_URL, attachment.file.url) for attachment in post.attachments.all()]

    response = httpx.post(
        f"{settings.SOCIAL_PUBLISHER_BASE_URL}/v1/posts/publish",
        json={
            "text": post.common_social_text or post.text,
            "platform_text": {
                "facebook": post.meta_text,
                "instagram": post.meta_text,
                "telegram": post.telegram_text,
            },
            "media_urls": media_urls,
            "platforms": ["all"],
        },
        headers=_headers(),
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["results"]
