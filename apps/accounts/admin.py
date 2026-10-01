from django.contrib import admin

from .models import WebAuthnCredential


@admin.register(WebAuthnCredential)
class WebAuthnCredentialAdmin(admin.ModelAdmin):
    list_display = ("user", "device_name", "created_at", "last_used_at")
    readonly_fields = ("credential_id", "public_key", "sign_count", "created_at", "last_used_at")
    search_fields = ("user__username", "device_name")
