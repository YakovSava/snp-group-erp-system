import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import agent
from ..config import get_settings
from ..db import get_db
from ..deps import require_service_token
from ..files import extract as file_extract
from ..models import Conversation, Message
from ..schemas import ChatResponse, ConversationOut, MessageOut

router = APIRouter(prefix="/v1", dependencies=[Depends(require_service_token)])


def _save_upload(data: bytes, filename: str) -> str:
    settings = get_settings()
    os.makedirs(settings.media_root, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{filename}"
    path = os.path.join(settings.media_root, safe_name)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


@router.post("/chat", response_model=ChatResponse)
def chat(
    external_user_id: str = Form(...),
    message: str = Form(...),
    conversation_id: int | None = Form(default=None),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    # Plain `def`, not `async def`: everything below (SQLAlchemy, the LLM
    # client, file I/O) is synchronous/blocking, and FastAPI runs sync path
    # operations in a thread pool — an async def here would block the whole
    # event loop for the duration of every LLM call.
    attachments: list[agent.AttachmentInput] = []
    for upload in files:
        data = upload.file.read()
        mime = file_extract.sniff_mime(data)
        path = _save_upload(data, upload.filename or "file")
        extracted = None if file_extract.is_image(mime) else file_extract.extract_text(data, mime)
        attachments.append(
            agent.AttachmentInput(
                original_filename=upload.filename or "file",
                mime_type=mime,
                data=data,
                file_path=path,
                extracted_text=extracted,
            )
        )

    conversation, assistant_message = agent.handle_chat_turn(
        db=db,
        conversation_id=conversation_id,
        external_user_id=external_user_id,
        message=message,
        attachments=attachments,
    )

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        reply=assistant_message.content,
        attachments=[a.file_path for a in assistant_message.attachments],
    )


@router.get("/conversations/{external_user_id}", response_model=list[ConversationOut])
def list_conversations(external_user_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Conversation)
        .filter(Conversation.external_user_id == external_user_id)
        .order_by(Conversation.created_at.desc())
        .all()
    )


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(conversation_id: int, db: Session = Depends(get_db)):
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation.messages
