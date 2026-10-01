import base64
import json
import re

from fastapi import APIRouter, Depends, Form, UploadFile

from .. import llm_client
from ..deps import require_service_token
from ..schemas import SmmDraftResponse

router = APIRouter(prefix="/v1", dependencies=[Depends(require_service_token)])

EDIT_PROMPT_TEMPLATE = (
    "Это фотография товара для карточки интернет-магазина и поста в соцсетях, "
    "снятая в плохом качестве (возможно, с водяными знаками и неаккуратным фоном). "
    "Перерисуй изображение: убери любые водяные знаки и посторонние надписи, "
    "сделай фон полностью белым и чистым (студийный стиль), заметно улучши резкость, "
    "контраст и общее качество. Не меняй сам товар — его форму, цвет, пропорции и детали "
    "оставь как есть, редактируй только фон и качество картинки."
    "{extra}"
)

COPY_PROMPT = (
    "Ты — SMM-специалист компании SNP (поставщик спецтехники и запчастей для грузовой "
    "техники). Посмотри на фото товара и прочитай описание ниже, затем подготовь "
    "материалы для поста о новом товаре в ассортименте.\n\n"
    "Описание товара от сотрудника (может быть неполным, с опечатками или на другом "
    "языке):\n{description}\n\n"
    'Верни ТОЛЬКО JSON без пояснений, строго в виде:\n'
    '{{"post_text": "...", "instagram_text": "...", "telegram_text": "...", '
    '"facebook_text": "...", "common_social_text": "..."}}\n\n'
    'post_text — основной текст поста на русском, начинается с "🆕 Новый товар в '
    'ассортименте" и затем даёт точное, грамотно оформленное описание товара на основе '
    "фото и описания. instagram_text — живой тон с эмодзи и релевантными хэштегами. "
    "telegram_text — короткий и по делу. facebook_text — чуть более развёрнутый, с "
    "деталями. common_social_text — нейтральный универсальный вариант для остальных "
    "площадок. Все поля на русском языке."
)

_DEFAULT_COPY = {
    "post_text": "🆕 Новый товар в ассортименте.",
    "instagram_text": "",
    "telegram_text": "",
    "facebook_text": "",
    "common_social_text": "",
}


def _parse_copy_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return dict(_DEFAULT_COPY)
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return dict(_DEFAULT_COPY)
    return {key: str(parsed.get(key) or default) for key, default in _DEFAULT_COPY.items()}


@router.post("/smm/draft", response_model=SmmDraftResponse)
def generate_smm_draft(
    image: UploadFile,
    description: str = Form(...),
    refine_instructions: str = Form(default=""),
):
    """Cleans up a (usually bad-quality) product photo and drafts social-post
    copy from it + a free-text description. Called once to generate the
    initial draft, then again (with refine_instructions, and the previous
    result as `image`) each time the user asks for further improvement —
    see apps.agent.smm in auto-smm for the review/accept loop.
    """
    original_bytes = image.file.read()

    extra = f" Дополнительно: {refine_instructions}" if refine_instructions else ""
    edited_bytes = llm_client.edit_image(original_bytes, prompt=EDIT_PROMPT_TEMPLATE.format(extra=extra))

    vision_content = llm_client.build_vision_content(
        COPY_PROMPT.format(description=description), [original_bytes]
    )
    raw = llm_client.raw_completion([{"role": "user", "content": vision_content}])
    copy_fields = _parse_copy_json(raw)

    return SmmDraftResponse(image_b64=base64.b64encode(edited_bytes).decode(), **copy_fields)
