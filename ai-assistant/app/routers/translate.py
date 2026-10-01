from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import llm_client
from ..currency.convert import annotate_amd_amounts_with_usd
from ..db import get_db
from ..deps import require_service_token
from ..schemas import TranslateRequest, TranslateResponse

router = APIRouter(prefix="/v1", dependencies=[Depends(require_service_token)])

LANGUAGE_NAMES = {"ru": "русский", "en": "английский", "hy": "армянский"}

_TRANSLATE_PROMPT = (
    "Переведи следующий текст на {language}. Сохрани тон, эмодзи, хэштеги и форматирование. "
    "Верни ТОЛЬКО переведённый текст, без пояснений и кавычек.\n\nТекст:\n{text}"
)


@router.post("/translate", response_model=TranslateResponse)
def translate(payload: TranslateRequest, db: Session = Depends(get_db)):
    language_name = LANGUAGE_NAMES.get(payload.target_language, payload.target_language)
    prompt = _TRANSLATE_PROMPT.format(language=language_name, text=payload.text)
    translated = llm_client.raw_completion([{"role": "user", "content": prompt}]).strip()

    if payload.annotate_amd_with_usd:
        translated = annotate_amd_amounts_with_usd(db, translated)

    return TranslateResponse(text=translated)
