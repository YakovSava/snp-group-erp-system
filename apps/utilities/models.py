import os
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def conversion_source_path(instance, filename):
    return f"conversions/{instance.kind}/source/{filename}"


def conversion_result_path(instance, filename):
    return f"conversions/{instance.kind}/result/{filename}"


class ConversionJob(models.Model):
    """A single upload→convert→download job.

    Both the uploaded source file and the converted result live on disk only
    for CONVERSION_FILE_TTL_MINUTES (default 30) — cleaned up by a Celery
    Beat task. ConversionHistory keeps a permanent audit trail independently.
    """

    KIND_IMAGE = "image"
    KIND_VIDEO = "video"
    KIND_DOCUMENT = "document"
    KIND_CHOICES = [
        (KIND_IMAGE, _("Фото")),
        (KIND_VIDEO, _("Видео")),
        (KIND_DOCUMENT, _("Файл")),
    ]

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_DONE = "done"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, _("В очереди")),
        (STATUS_PROCESSING, _("Обрабатывается")),
        (STATUS_DONE, _("Готово")),
        (STATUS_FAILED, _("Ошибка")),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversion_jobs",
    )
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    source_file = models.FileField(upload_to=conversion_source_path)
    detected_source_format = models.CharField(max_length=20, blank=True)
    target_format = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_message = models.TextField(blank=True)
    result_file = models.FileField(upload_to=conversion_result_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Задача конвертации")
        verbose_name_plural = _("Задачи конвертации")

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and self.expires_at is None:
            self.expires_at = self.created_at + timedelta(minutes=settings.CONVERSION_FILE_TTL_MINUTES)
            super().save(update_fields=["expires_at"])

    @property
    def is_expired(self):
        return self.expires_at is not None and timezone.now() >= self.expires_at

    @property
    def source_filename(self):
        return os.path.basename(self.source_file.name)

    def __str__(self):
        return f"{self.get_kind_display()} #{self.pk} ({self.status})"


class ConversionHistory(models.Model):
    """Permanent audit log: who converted what into what."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="conversion_history",
    )
    action = models.TextField(_("Что сделал"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("История")
        verbose_name_plural = _("История")

    def __str__(self):
        return self.action
