"""Thin client for the ai-assistant microservice.

ai-assistant is a separate service/deployment (see ai-assistant/) reached
over plain HTTP with a shared service token — never exposed to the browser;
Django is the only caller.
"""
import httpx
from django.conf import settings

DEFAULT_TIMEOUT = 30.0


def _headers():
    return {"X-Service-Token": settings.AI_ASSISTANT_SERVICE_TOKEN}


def translate(text: str, target_language: str, annotate_amd_with_usd: bool = False) -> str:
    response = httpx.post(
        f"{settings.AI_ASSISTANT_BASE_URL}/v1/translate",
        json={
            "text": text,
            "target_language": target_language,
            "annotate_amd_with_usd": annotate_amd_with_usd,
        },
        headers=_headers(),
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["text"]


def chat(external_user_id: str, message: str, conversation_id: int | None = None, files: list | None = None) -> dict:
    data = {"external_user_id": external_user_id, "message": message}
    if conversation_id:
        data["conversation_id"] = conversation_id
    file_tuples = [("files", (f.name, f.read(), f.content_type)) for f in (files or [])]
    response = httpx.post(
        f"{settings.AI_ASSISTANT_BASE_URL}/v1/chat",
        data=data,
        files=file_tuples or None,
        headers=_headers(),
        # ai-assistant retries its own gateway calls up to 3x, honoring the
        # gateway's own "retry_after" backoff (observed up to 30s, capped)
        # on top of request time — this needs enough headroom for that.
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()


def list_conversations(external_user_id: str) -> list:
    response = httpx.get(
        f"{settings.AI_ASSISTANT_BASE_URL}/v1/conversations/{external_user_id}",
        headers=_headers(),
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def generate_smm_draft(
    description: str,
    image_bytes: bytes,
    filename: str = "photo.jpg",
    refine_instructions: str = "",
) -> dict:
    """Cleans up a product photo and drafts post copy from it + description.

    Used both for the initial draft (image_bytes = the raw uploaded photo)
    and for "improve further" refinement (image_bytes = the previous draft's
    image, refine_instructions = the user's extra instructions) — ai-assistant
    doesn't track draft state itself, so Django resends whatever the current
    image is each time.
    """
    response = httpx.post(
        f"{settings.AI_ASSISTANT_BASE_URL}/v1/smm/draft",
        data={"description": description, "refine_instructions": refine_instructions},
        files={"image": (filename, image_bytes, "image/jpeg")},
        headers=_headers(),
        # Two sequential gateway calls (image edit, then vision copy
        # generation), each independently retried up to 3x with up to ~30s
        # backoff per retry when the gateway asks for it — worst case is
        # comfortably under this.
        timeout=220.0,
    )
    response.raise_for_status()
    return response.json()


def get_messages(conversation_id: int) -> list:
    response = httpx.get(
        f"{settings.AI_ASSISTANT_BASE_URL}/v1/conversations/{conversation_id}/messages",
        headers=_headers(),
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()
