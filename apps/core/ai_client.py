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
        timeout=60.0,  # image generation/editing turns can run long
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


def get_messages(conversation_id: int) -> list:
    response = httpx.get(
        f"{settings.AI_ASSISTANT_BASE_URL}/v1/conversations/{conversation_id}/messages",
        headers=_headers(),
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()
