import datetime

from pydantic import BaseModel


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: int
    external_user_id: str
    title: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    conversation_id: int
    message_id: int
    reply: str
    attachments: list[str] = []


class TranslateRequest(BaseModel):
    text: str
    target_language: str  # "en" | "hy" | "ru"
    annotate_amd_with_usd: bool = False


class TranslateResponse(BaseModel):
    text: str


class ConvertCurrencyRequest(BaseModel):
    amount: float | None = None
    text: str | None = None
    from_currency: str | None = None
    to_currency: str | None = None


class ConvertedAmount(BaseModel):
    original_amount: float
    original_currency: str
    converted_amount: float
    converted_currency: str
    rate_used: float
    rate_source: str


class ConvertCurrencyResponse(BaseModel):
    result: ConvertedAmount | None = None
    rewritten_text: str | None = None
    detected: list[ConvertedAmount] = []


class KnowledgeIngestRequest(BaseModel):
    title: str
    text: str


class KnowledgeIngestResponse(BaseModel):
    chunks_ingested: int


class SmmDraftResponse(BaseModel):
    image_b64: str
    post_text: str
    meta_text: str
    telegram_text: str
    common_social_text: str


class SalesTitleRequest(BaseModel):
    text: str


class SalesTitleResponse(BaseModel):
    title: str


class CatalogMappingRequest(BaseModel):
    headers: list[str]
    sample_rows: list[list[str]]


class CatalogMappingResponse(BaseModel):
    # One entry per input column, in order — each one of CATALOG_COLUMN_FIELDS
    # (see routers/catalog.py). The employee reviews/corrects this before
    # anything is imported, so a wrong guess here is cheap to fix.
    column_fields: list[str]
    amount_rub_markup_percent: float | None = None
    amount_usd_markup_percent: float | None = None
    notes: str = ""
