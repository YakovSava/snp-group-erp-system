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
