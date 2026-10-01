import base64
import io

from openai import OpenAI

from .config import get_settings

_settings = get_settings()
_client = OpenAI(base_url=_settings.ai_base_url, api_key=_settings.ai_api_key)

SYSTEM_PROMPT = (
    "Ты — внутренний AI-ассистент компании SNP (поставщик спецтехники и запчастей). "
    "Отвечай в формате Markdown (заголовки, списки, таблицы, код по необходимости). "
    "Отвечай на том языке, на котором пишет пользователь, если явно не попросили иначе. "
    "Будь точным и лаконичным."
)


def chat(messages: list[dict], model: str | None = None) -> str:
    response = _client.chat.completions.create(
        model=model or _settings.default_chat_model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
    )
    return response.choices[0].message.content or ""


def raw_completion(messages: list[dict], model: str | None = None) -> str:
    """Chat call without the assistant system prompt — for internal
    extraction/classification tasks (currency parsing, translation) where we
    want a clean, task-specific instruction instead of the chat persona.
    """
    response = _client.chat.completions.create(
        model=model or _settings.default_chat_model,
        messages=messages,
    )
    return response.choices[0].message.content or ""


def edit_image(image_bytes: bytes, prompt: str, model: str | None = None) -> bytes:
    image_file = io.BytesIO(image_bytes)
    image_file.name = "image.png"

    result = _client.images.edit(
        model=model or _settings.default_image_model,
        image=image_file,
        prompt=prompt,
    )
    b64 = result.data[0].b64_json
    return base64.b64decode(b64)


def generate_image(prompt: str, model: str | None = None) -> bytes:
    result = _client.images.generate(
        model=model or _settings.default_image_model,
        prompt=prompt,
        n=1,
    )
    b64 = result.data[0].b64_json
    return base64.b64decode(b64)
