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

DRAFT_TEXT_FIELDS = ["post_text", "meta_text", "telegram_text", "common_social_text"]
VALID_CURRENCIES = ("AMD", "RUB", "USD")


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


def _parse_price(request):
    """Returns (amount_str, currency, error_message). Price is mandatory —
    a priced post can't be generated without it, and callers must surface
    error_message to the user rather than falling back to a guess.

    amount_str is kept as a (normalized) string rather than a float: it's
    only ever displayed or sent back out over HTTP, and this sidesteps
    float formatting surprises (e.g. "45000.0") in the generated copy.
    """
    price_amount = request.POST.get("price_amount", "").strip().replace(",", ".")
    price_currency = request.POST.get("price_currency", "").strip().upper()
    if not price_amount or price_currency not in VALID_CURRENCIES:
        return None, None, _("Укажите цену товара и валюту.")
    try:
        amount = float(price_amount)
    except ValueError:
        return None, None, _("Цена должна быть числом.")
    if amount <= 0:
        return None, None, _("Цена должна быть больше нуля.")
    normalized = f"{amount:.0f}" if amount == int(amount) else f"{amount:g}"
    return normalized, price_currency, None


@login_required
@require_POST
def smm_generate(request):
    description = request.POST.get("description", "").strip()
    photo = request.FILES.get("photo")
    price_amount, price_currency, price_error = _parse_price(request)
    if not description or not photo:
        return JsonResponse({"error": _("Нужны и фото, и описание товара.")}, status=400)
    if price_error:
        return JsonResponse({"error": price_error}, status=400)

    try:
        result = ai_client.generate_smm_draft(
            description=description,
            image_bytes=photo.read(),
            price_amount=price_amount,
            price_currency=price_currency,
            filename=photo.name,
        )
    except httpx.HTTPError:
        return JsonResponse({"error": _("AI-ассистент временно недоступен. Попробуйте позже.")}, status=502)

    _discard_draft(request)
    relative_path = _save_draft_image(base64.b64decode(result["image_b64"]))

    draft = {
        "image_path": relative_path,
        "description": description,
        "price_amount": price_amount,
        "price_currency": price_currency,
    }
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
    # Price can be corrected before asking for another round — if the
    # employee didn't touch it, reuse what's already on the draft.
    if request.POST.get("price_amount"):
        price_amount, price_currency, price_error = _parse_price(request)
        if price_error:
            return JsonResponse({"error": price_error}, status=400)
    else:
        price_amount, price_currency = draft["price_amount"], draft["price_currency"]

    with open(_draft_abspath(draft["image_path"]), "rb") as fh:
        current_bytes = fh.read()

    try:
        result = ai_client.generate_smm_draft(
            description=draft["description"],
            image_bytes=current_bytes,
            price_amount=price_amount,
            price_currency=price_currency,
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
    draft["price_amount"] = price_amount
    draft["price_currency"] = price_currency
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
            meta_text=request.POST.get("meta_text", draft["meta_text"]),
            telegram_text=request.POST.get("telegram_text", draft["telegram_text"]),
            common_social_text=request.POST.get("common_social_text", draft["common_social_text"]),
            price_amount=request.POST.get("price_amount", draft["price_amount"]),
            price_currency=request.POST.get("price_currency", draft["price_currency"]),
            send_to_marketplace=send_to_marketplace,
            created_by=request.user,
        )
        with open(_draft_abspath(draft["image_path"]), "rb") as fh:
            PostAttachment.objects.create(post=post, file=ContentFile(fh.read(), name="product.jpg"))

    _discard_draft(request)

    return JsonResponse({"status": "ok", "redirect_url": reverse("posts:post_detail", args=[post.pk])})
