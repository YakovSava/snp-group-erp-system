import base64
import os
import uuid

import httpx
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.core import ai_client
from apps.posts.models import Post, PostAttachment

SESSION_DRAFT_KEY = "smm_draft"
DRAFT_SUBDIR = "smm_drafts"

DRAFT_TEXT_FIELDS = ["post_text", "instagram_text", "telegram_text", "facebook_text", "common_social_text"]


def _draft_abspath(relative_path):
    return os.path.join(settings.MEDIA_ROOT, relative_path)


def _save_draft_image(image_bytes: bytes) -> str:
    draft_dir = os.path.join(settings.MEDIA_ROOT, DRAFT_SUBDIR)
    os.makedirs(draft_dir, exist_ok=True)
    relative_path = f"{DRAFT_SUBDIR}/{uuid.uuid4().hex}.jpg"
    with open(_draft_abspath(relative_path), "wb") as fh:
        fh.write(image_bytes)
    return relative_path


def _discard_draft(request):
    draft = request.session.get(SESSION_DRAFT_KEY)
    if draft and draft.get("image_path"):
        try:
            os.remove(_draft_abspath(draft["image_path"]))
        except OSError:
            pass
    request.session.pop(SESSION_DRAFT_KEY, None)


def _draft_payload(draft):
    return {**draft, "image_url": settings.MEDIA_URL + draft["image_path"]}


@login_required
def smm_tool_page(request):
    draft = request.session.get(SESSION_DRAFT_KEY)
    return render(request, "agent/smm_tool.html", {"draft": _draft_payload(draft) if draft else None})


@login_required
@require_POST
def smm_generate(request):
    description = request.POST.get("description", "").strip()
    photo = request.FILES.get("photo")
    if not description or not photo:
        return JsonResponse({"error": _("Нужны и фото, и описание товара.")}, status=400)

    try:
        result = ai_client.generate_smm_draft(
            description=description, image_bytes=photo.read(), filename=photo.name
        )
    except httpx.HTTPError:
        return JsonResponse({"error": _("AI-ассистент временно недоступен. Попробуйте позже.")}, status=502)

    _discard_draft(request)
    relative_path = _save_draft_image(base64.b64decode(result["image_b64"]))

    draft = {"image_path": relative_path, "description": description}
    draft.update({field: result[field] for field in DRAFT_TEXT_FIELDS})
    request.session[SESSION_DRAFT_KEY] = draft

    return JsonResponse({"draft": _draft_payload(draft)})


@login_required
@require_POST
def smm_refine(request):
    draft = request.session.get(SESSION_DRAFT_KEY)
    if not draft:
        return JsonResponse({"error": _("Сначала создайте черновик.")}, status=400)

    refine_instructions = request.POST.get("refine_instructions", "").strip()
    with open(_draft_abspath(draft["image_path"]), "rb") as fh:
        current_bytes = fh.read()

    try:
        result = ai_client.generate_smm_draft(
            description=draft["description"],
            image_bytes=current_bytes,
            filename="draft.jpg",
            refine_instructions=refine_instructions,
        )
    except httpx.HTTPError:
        return JsonResponse({"error": _("AI-ассистент временно недоступен. Попробуйте позже.")}, status=502)

    old_path = _draft_abspath(draft["image_path"])
    new_relative_path = _save_draft_image(base64.b64decode(result["image_b64"]))
    try:
        os.remove(old_path)
    except OSError:
        pass

    draft["image_path"] = new_relative_path
    draft.update({field: result[field] for field in DRAFT_TEXT_FIELDS})
    request.session[SESSION_DRAFT_KEY] = draft

    return JsonResponse({"draft": _draft_payload(draft)})


@login_required
@require_POST
def smm_discard(request):
    _discard_draft(request)
    return JsonResponse({"status": "ok"})


@login_required
@require_POST
def smm_accept(request):
    draft = request.session.get(SESSION_DRAFT_KEY)
    if not draft:
        return JsonResponse({"error": _("Черновик не найден.")}, status=400)

    send_to_marketplace = request.POST.get("send_to_marketplace") == "on"

    with transaction.atomic():
        post = Post.objects.create(
            text=request.POST.get("post_text", draft["post_text"]),
            instagram_text=request.POST.get("instagram_text", draft["instagram_text"]),
            telegram_text=request.POST.get("telegram_text", draft["telegram_text"]),
            facebook_text=request.POST.get("facebook_text", draft["facebook_text"]),
            common_social_text=request.POST.get("common_social_text", draft["common_social_text"]),
            send_to_marketplace=send_to_marketplace,
            created_by=request.user,
        )
        with open(_draft_abspath(draft["image_path"]), "rb") as fh:
            PostAttachment.objects.create(post=post, file=ContentFile(fh.read(), name="product.jpg"))

    _discard_draft(request)

    return JsonResponse({"status": "ok", "redirect_url": reverse("posts:post_detail", args=[post.pk])})
