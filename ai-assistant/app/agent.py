import base64
import dataclasses
import os
import uuid

from sqlalchemy.orm import Session

from . import llm_client
from .config import get_settings
from .models import Conversation, Message, MessageAttachment, MessageRole
from .rag import store as rag_store

HISTORY_LIMIT = 20
RAG_RESULTS = 3
RAG_DISTANCE_THRESHOLD = 0.45  # cosine distance; lower = more similar

IMAGE_EDIT_KEYWORDS = [
    "измени", "редактир", "отредактир", "удали фон", "поменяй фон", "перекрась",
    "убери", "замени", "раскрась", "улучши",
    "edit", "retouch", "remove background", "enhance", "recolor",
]


@dataclasses.dataclass
class AttachmentInput:
    original_filename: str
    mime_type: str
    data: bytes
    file_path: str
    extracted_text: str | None = None


def _looks_like_image_edit_request(message: str) -> bool:
    lowered = message.lower()
    return any(keyword in lowered for keyword in IMAGE_EDIT_KEYWORDS)


def get_or_create_conversation(db: Session, conversation_id: int | None, external_user_id: str) -> Conversation:
    if conversation_id:
        conversation = db.get(Conversation, conversation_id)
        if conversation is not None:
            return conversation
    conversation = Conversation(external_user_id=external_user_id, title="")
    db.add(conversation)
    db.flush()
    return conversation


def _save_attachment(db: Session, message: Message, attachment: AttachmentInput) -> None:
    db.add(
        MessageAttachment(
            message_id=message.id,
            file_path=attachment.file_path,
            original_filename=attachment.original_filename,
            mime_type=attachment.mime_type,
            extracted_text=attachment.extracted_text,
        )
    )


def _build_history(db: Session, conversation: Conversation) -> list[dict]:
    recent = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    recent.reverse()
    return [{"role": m.role.value, "content": m.content} for m in recent]


def _rag_context(db: Session, query_text: str) -> str:
    hits = rag_store.query(query_text, n_results=RAG_RESULTS)
    relevant = [h for h in hits if h["distance"] <= RAG_DISTANCE_THRESHOLD]
    if not relevant:
        return ""
    joined = "\n\n".join(f"[{h['metadata'].get('title', '?')}] {h['text']}" for h in relevant)
    return (
        "Ниже приведены релевантные фрагменты из базы знаний компании. "
        "Используй их, если они отвечают на вопрос пользователя:\n\n" + joined
    )


def handle_chat_turn(
    db: Session,
    conversation_id: int | None,
    external_user_id: str,
    message: str,
    attachments: list[AttachmentInput],
) -> tuple[Conversation, Message]:
    conversation = get_or_create_conversation(db, conversation_id, external_user_id)
    if not conversation.title:
        conversation.title = message[:60]

    user_message = Message(conversation_id=conversation.id, role=MessageRole.USER, content=message)
    db.add(user_message)
    db.flush()
    for attachment in attachments:
        _save_attachment(db, user_message, attachment)

    image_attachments = [a for a in attachments if a.mime_type.startswith("image/")]
    reply_attachments: list[AttachmentInput] = []

    if image_attachments and _looks_like_image_edit_request(message):
        settings = get_settings()
        edited_bytes = llm_client.edit_image(image_attachments[0].data, prompt=message)
        filename = f"{uuid.uuid4().hex}.png"
        path = os.path.join(settings.media_root, filename)
        with open(path, "wb") as fh:
            fh.write(edited_bytes)
        reply_text = "Готово — вот отредактированное изображение."
        reply_attachments.append(
            AttachmentInput(
                original_filename=filename,
                mime_type="image/png",
                data=edited_bytes,
                file_path=path,
            )
        )
    else:
        history = _build_history(db, conversation)
        context_blocks = []

        for attachment in attachments:
            if attachment.extracted_text:
                context_blocks.append(
                    f"[Содержимое файла {attachment.original_filename}]:\n{attachment.extracted_text[:6000]}"
                )

        rag_context = _rag_context(db, message)
        if rag_context:
            context_blocks.append(rag_context)

        user_content: object = message
        if image_attachments:
            # Vision input: let the model see the image directly (Q&A, not an edit).
            parts = [{"type": "text", "text": message}]
            for attachment in image_attachments:
                b64 = base64.b64encode(attachment.data).decode()
                parts.append(
                    {"type": "image_url", "image_url": {"url": f"data:{attachment.mime_type};base64,{b64}"}}
                )
            user_content = parts

        llm_messages = list(history[:-1])  # history includes the just-added user turn; replace its content below
        if context_blocks:
            llm_messages.append({"role": "system", "content": "\n\n".join(context_blocks)})
        llm_messages.append({"role": "user", "content": user_content})

        reply_text = llm_client.chat(llm_messages)

    assistant_message = Message(conversation_id=conversation.id, role=MessageRole.ASSISTANT, content=reply_text)
    db.add(assistant_message)
    db.flush()
    for attachment in reply_attachments:
        _save_attachment(db, assistant_message, attachment)

    db.commit()
    return conversation, assistant_message
