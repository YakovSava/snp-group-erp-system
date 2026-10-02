import base64
import json
import re

from fastapi import APIRouter, Depends, Form, UploadFile

from .. import llm_client
from ..deps import require_service_token
from ..rag import store as rag_store
from ..schemas import SalesTitleRequest, SalesTitleResponse, SmmDraftResponse

router = APIRouter(prefix="/v1", dependencies=[Depends(require_service_token)])

RAG_RESULTS = 3
RAG_DISTANCE_THRESHOLD = 0.45  # cosine distance; lower = more similar

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
    "Цена товара: {price_amount} {price_currency}. Эта цена ОБЯЗАТЕЛЬНО должна быть "
    "упомянута в каждом тексте ниже (post_text, meta_text — во всех трёх языковых "
    "блоках, telegram_text, common_social_text) — пост без цены публиковать нельзя. "
    "Используй ровно эту сумму и валюту, ничего не придумывай и не пересчитывай в "
    "другую валюту — переводи только название валюты на язык блока (AMD -> драм/դրամ, "
    "RUB -> рублей, USD -> долларов).\n"
    "{knowledge_block}\n"
    'Верни ТОЛЬКО JSON без пояснений, строго в виде:\n'
    '{{"post_text": "...", "meta_text": "...", "telegram_text": "...", '
    '"common_social_text": "..."}}\n\n'
    "post_text — основной текст поста на русском, начинается с \"🆕 Новый товар в "
    "ассортименте\" и даёт точное, грамотно оформленное описание товара на основе фото "
    "и описания, с указанием цены.\n\n"
    "meta_text — ОДИН общий текст для Facebook и Instagram (публикуется без изменений "
    "на обеих площадках). Состоит из трёх блоков подряд в этом порядке: русский, "
    "армянский, английский — блоки разделены строкой '---' на отдельной строке. "
    "Каждый блок строится строго по этой структуре и сохраняет эмодзи:\n"
    "🆕 <новое поступление: название товара, артикул, бренд, применяемость — на языке "
    "блока>\n"
    "<1-2 предложения живого описания товара на языке блока>\n"
    "📋 <слово «Характеристики» на языке блока>:\n"
    "▫️ <Артикул на языке блока>: ...\n"
    "▫️ <Производитель на языке блока>: ...\n"
    "▫️ <Применяемость на языке блока>: ...\n"
    "▫️ <остальные значимые характеристики из описания/фото, по одной строке на "
    "каждую>\n"
    "✅ <товар доступен к заказу со склада SNP, на языке блока>.\n"
    "📩 <цена {price_amount} {price_currency} на языке блока>. <как связаться: Direct, "
    "Telegram или WhatsApp +374 93 36-00-83>\n\n"
    "telegram_text — ОТДЕЛЬНЫЙ короткий текст на русском (3-5 строк), по-другому "
    "сформулированный и по-другому построенный, чем meta_text: без блока характеристик "
    "списком, по делу, с ценой.\n\n"
    "common_social_text — нейтральный универсальный короткий вариант на русском для "
    "остальных площадок, тоже с ценой.\n\n"
    "Все текстовые поля, кроме армянского и английского блоков внутри meta_text, пиши "
    "на русском языке."
)

SALES_TITLE_PROMPT = (
    "На основе текста поста о товаре ниже составь короткий заголовок (строго до 70 "
    "символов, без эмодзи и кавычек) для карточки товара на list.am/avito: бренд, "
    "название/тип товара, артикул и применяемость, в стиле обычных объявлений на этих "
    "площадках. Верни ТОЛЬКО сам заголовок, без пояснений.\n\nТекст поста:\n{text}"
)

_DEFAULT_COPY = {
    "post_text": "🆕 Новый товар в ассортименте.",
    "meta_text": "",
    "telegram_text": "",
    "common_social_text": "",
}


def _rag_context(query_text: str) -> str:
    hits = rag_store.query(query_text, n_results=RAG_RESULTS)
    relevant = [h for h in hits if h["distance"] <= RAG_DISTANCE_THRESHOLD]
    if not relevant:
        return ""
    joined = "\n\n".join(f"[{h['metadata'].get('title', '?')}] {h['text']}" for h in relevant)
    return (
        "Ниже приведены релевантные фрагменты из базы знаний компании. Используй их "
        "для точных формулировок и характеристик, если они относятся к этому товару:\n\n"
        + joined
        + "\n"
    )


def _parse_copy_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return dict(_DEFAULT_COPY)
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return dict(_DEFAULT_COPY)
    return {key: str(parsed.get(key) or default) for key, default in _DEFAULT_COPY.items()}


def _price_marker(price_amount: str) -> str:
    """Digits of the price amount with separators stripped, for a
    best-effort "is the price actually in this text" check.
    """
    return re.sub(r"[^\d]", "", price_amount)


def _ensure_price_present(text: str, price_amount: str, price_currency: str) -> str:
    """The price is a hard business requirement, not a suggestion — if the
    model dropped it (or formatted the number in a way our marker check
    misses), append it rather than ship a priced post with no price.
    """
    marker = _price_marker(price_amount)
    if not text or not marker or marker in re.sub(r"[^\d]", "", text):
        return text
    return f"{text}\n\n💰 Цена: {price_amount} {price_currency}"


@router.post("/smm/draft", response_model=SmmDraftResponse)
def generate_smm_draft(
    image: UploadFile,
    description: str = Form(...),
    price_amount: str = Form(...),
    price_currency: str = Form(...),
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

    knowledge_block = _rag_context(description)
    prompt = COPY_PROMPT.format(
        description=description,
        price_amount=price_amount,
        price_currency=price_currency,
        knowledge_block=knowledge_block,
    )
    vision_content = llm_client.build_vision_content(prompt, [original_bytes])
    raw = llm_client.raw_completion([{"role": "user", "content": vision_content}])
    copy_fields = _parse_copy_json(raw)
    copy_fields = {
        key: _ensure_price_present(value, price_amount, price_currency)
        for key, value in copy_fields.items()
    }

    return SmmDraftResponse(image_b64=base64.b64encode(edited_bytes).decode(), **copy_fields)


@router.post("/smm/sales-title", response_model=SalesTitleResponse)
def generate_sales_title(payload: SalesTitleRequest):
    """Short list.am/avito card title derived from a post's text — used by
    apps.posts.tasks.create_sales_post_from_post instead of a hardcoded
    placeholder when auto-mirroring a Post into a SalesPost.
    """
    raw = llm_client.raw_completion(
        [{"role": "user", "content": SALES_TITLE_PROMPT.format(text=payload.text)}]
    )
    title = raw.strip().strip('"').strip()
    return SalesTitleResponse(title=title[:255])
