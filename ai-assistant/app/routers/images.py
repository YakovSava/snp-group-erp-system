from fastapi import APIRouter, Depends, Form, UploadFile
from fastapi.responses import Response

from .. import llm_client
from ..config import get_settings
from ..deps import require_service_token

router = APIRouter(prefix="/v1", dependencies=[Depends(require_service_token)])


@router.post("/images/edit")
def edit_image(
    image: UploadFile,
    prompt: str = Form(...),
    high_quality: bool = Form(default=False),
):
    # Plain `def` — see chat.py for why (blocking LLM call must not run on
    # the event loop).
    settings = get_settings()
    data = image.file.read()
    model = settings.high_quality_image_model if high_quality else settings.default_image_model
    edited = llm_client.edit_image(data, prompt=prompt, model=model)
    return Response(content=edited, media_type="image/png")
