from django.conf import settings
from django.db import models


class WebAuthnCredential(models.Model):
    """A single registered PassKey for a user.

    Passwords remain the primary login method (admin-provisioned accounts,
    no public sign-up); a user may optionally add one or more passkeys for
    themselves from the Security page for convenience.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="webauthn_credentials",
    )
    credential_id = models.CharField(max_length=255, unique=True)
    public_key = models.TextField()
    sign_count = models.PositiveBigIntegerField(default=0)
    device_name = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "PassKey"
        verbose_name_plural = "PassKeys"

    def __str__(self):
        return f"{self.device_name or 'Passkey'} ({self.user})"
