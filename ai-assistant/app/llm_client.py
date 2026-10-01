import base64
import io
import logging
import time

import openai
from openai import OpenAI

from .config import get_settings
from .files.image_prep import prepare_image_for_api

_settings = get_settings()
_client = OpenAI(base_url=_settings.ai_base_url, api_key=_settings.ai_api_key)

logger = logging.getLogger(__name__)

# The gateway's image endpoints (edit/generate, and vision input on chat)
# were confirmed flaky during testing — the SAME ~15KB image returned
# 520, 502, then 520 again on three immediate retries, while a slightly
# larger image succeeded once. This isn't a size cutoff, it's an unreliable
# backend, so every gateway call is retried with backoff rather than
# trusting the first response.
#
# Some 520s come back with a structured Cloudflare error body telling us
# exactly how long to back off — observed live: {'retryable': True,
# 'retry_after': 60, ...}. Our previous fixed 1.5/3/6s backoff ignored that
# entirely, which is nowhere near enough for a genuine origin-overload
# situation. We now honor retry_after when present, capped at
# MAX_SERVER_REQUESTED_WAIT_SECONDS so one slow gateway call can't blow past
# the httpx/gunicorn timeouts configured around it.
RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY_SECONDS = 1.5
MAX_SERVER_REQUESTED_WAIT_SECONDS = 30

SYSTEM_PROMPT = (
    "Ты — внутренний AI-ассистент компании SNP (поставщик спецтехники и запчастей). "
    "Отвечай в формате Markdown (заголовки, списки, таблицы, код по необходимости). "
    "Отвечай на том языке, на котором пишет пользователь, если явно не попросили иначе. "
    "Будь точным и лаконичным."
)


def _extract_retry_after(exc: Exception) -> float | None:
    """Pulls Cloudflare's suggested backoff out of the error body, when present."""
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        value = body.get("retry_after")
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _with_retries(func, *args, **kwargs):
    last_exc: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            return func(*args, **kwargs)
        except openai.APIError as exc:
            last_exc = exc
            if attempt < RETRY_ATTEMPTS - 1:
                retry_after = _extract_retry_after(exc)
                wait = (
                    min(retry_after, MAX_SERVER_REQUESTED_WAIT_SECONDS)
                    if retry_after is not None
                    else RETRY_BASE_DELAY_SECONDS * (2**attempt)
                )
                logger.warning(
                    "AI gateway call failed (attempt %s/%s), retrying in %.1fs: %s",
                    attempt + 1,
                    RETRY_ATTEMPTS,
                    wait,
                    exc,
                )
                time.sleep(wait)
    raise last_exc


def chat(messages: list[dict], model: str | None = None) -> str:
    response = _with_retries(
        _client.chat.completions.create,
        model=model or _settings.default_chat_model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
    )
    return response.choices[0].message.content or ""


def raw_completion(messages: list[dict], model: str | None = None) -> str:
    """Chat call without the assistant system prompt — for internal
    extraction/classification tasks (currency parsing, translation, SMM copy
    generation) where we want a clean, task-specific instruction instead of
    the chat persona.
    """
    response = _with_retries(
        _client.chat.completions.create,
        model=model or _settings.default_chat_model,
        messages=messages,
    )
    return response.choices[0].message.content or ""


def edit_image(image_bytes: bytes, prompt: str, model: str | None = None) -> bytes:
    prepared = prepare_image_for_api(image_bytes)
    image_file = io.BytesIO(prepared)
    image_file.name = "image.jpg"

    result = _with_retries(
        _client.images.edit,
        model=model or _settings.default_image_model,
        image=image_file,
        prompt=prompt,
    )
    b64 = result.data[0].b64_json
    return base64.b64decode(b64)


def generate_image(prompt: str, model: str | None = None) -> bytes:
    result = _with_retries(
        _client.images.generate,
        model=model or _settings.default_image_model,
        prompt=prompt,
        n=1,
    )
    b64 = result.data[0].b64_json
    return base64.b64decode(b64)


def build_vision_content(text: str, images: list[bytes], mime: str = "image/jpeg") -> list[dict]:
    """Builds a multimodal user message content array, compressing each
    image first (see files/image_prep.py).
    """
    parts: list[dict] = [{"type": "text", "text": text}]
    for image_bytes in images:
        prepared = prepare_image_for_api(image_bytes)
        b64 = base64.b64encode(prepared).decode()
        parts.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    return parts
