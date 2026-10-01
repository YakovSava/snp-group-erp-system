import json

from django.conf import settings
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

import webauthn
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from .models import WebAuthnCredential

SESSION_REGISTER_CHALLENGE = "webauthn_register_challenge"
SESSION_LOGIN_CHALLENGE = "webauthn_login_challenge"


class SnpLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class SnpLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")


@login_required
def security(request):
    credentials = request.user.webauthn_credentials.all()
    return render(request, "accounts/security.html", {"credentials": credentials})


@login_required
@require_POST
def credential_delete(request, pk):
    WebAuthnCredential.objects.filter(pk=pk, user=request.user).delete()
    return redirect("accounts:security")


@login_required
@require_POST
def webauthn_register_begin(request):
    existing = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(cred.credential_id))
        for cred in request.user.webauthn_credentials.all()
    ]
    options = webauthn.generate_registration_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        rp_name=settings.WEBAUTHN_RP_NAME,
        user_id=str(request.user.id).encode("utf-8"),
        user_name=request.user.get_username(),
        user_display_name=request.user.get_full_name() or request.user.get_username(),
        exclude_credentials=existing,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    request.session[SESSION_REGISTER_CHALLENGE] = bytes_to_base64url(options.challenge)
    return JsonResponse(json.loads(webauthn.options_to_json(options)))


@login_required
@require_POST
def webauthn_register_complete(request):
    challenge = request.session.pop(SESSION_REGISTER_CHALLENGE, None)
    if not challenge:
        return HttpResponseBadRequest(_("Регистрация устарела, попробуйте снова."))

    device_name = request.GET.get("device_name", "") or request.POST.get("device_name", "Passkey")

    try:
        verification = webauthn.verify_registration_response(
            credential=request.body,
            expected_challenge=base64url_to_bytes(challenge),
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGIN,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced to the user as a generic failure
        return JsonResponse({"error": str(exc)}, status=400)

    WebAuthnCredential.objects.create(
        user=request.user,
        credential_id=bytes_to_base64url(verification.credential_id),
        public_key=bytes_to_base64url(verification.credential_public_key),
        sign_count=verification.sign_count,
        device_name=device_name[:100],
    )
    return JsonResponse({"status": "ok"})


@require_POST
def webauthn_login_begin(request):
    options = webauthn.generate_authentication_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    request.session[SESSION_LOGIN_CHALLENGE] = bytes_to_base64url(options.challenge)
    return JsonResponse(json.loads(webauthn.options_to_json(options)))


@require_POST
def webauthn_login_complete(request):
    challenge = request.session.pop(SESSION_LOGIN_CHALLENGE, None)
    if not challenge:
        return HttpResponseBadRequest(_("Вход устарел, попробуйте снова."))

    try:
        payload = json.loads(request.body)
        raw_id = payload.get("rawId") or payload.get("id")
        credential_id = bytes_to_base64url(base64url_to_bytes(raw_id))
    except Exception:  # noqa: BLE001
        return HttpResponseBadRequest(_("Некорректный ответ устройства."))

    try:
        stored = WebAuthnCredential.objects.select_related("user").get(credential_id=credential_id)
    except WebAuthnCredential.DoesNotExist:
        return JsonResponse({"error": _("PassKey не зарегистрирован.")}, status=400)

    try:
        verification = webauthn.verify_authentication_response(
            credential=request.body,
            expected_challenge=base64url_to_bytes(challenge),
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGIN,
            credential_public_key=base64url_to_bytes(stored.public_key),
            credential_current_sign_count=stored.sign_count,
        )
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"error": str(exc)}, status=400)

    stored.sign_count = verification.new_sign_count
    stored.last_used_at = timezone.now()
    stored.save(update_fields=["sign_count", "last_used_at"])

    auth_login(request, stored.user, backend="django.contrib.auth.backends.ModelBackend")
    return JsonResponse({"status": "ok", "redirect": "/"})
