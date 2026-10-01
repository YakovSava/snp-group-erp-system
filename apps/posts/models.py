from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.file_validation import validate_post_attachment, validate_sales_attachment


def post_attachment_path(instance, filename):
    return f"posts/{instance.post_id}/{filename}"


def sales_attachment_path(instance, filename):
    return f"sales_posts/{instance.sales_post_id}/{filename}"


class Post(models.Model):
    """Пост в социальных сетях."""

    text = models.TextField(_("Основной текст"))

    instagram_text = models.TextField(_("Текст для Instagram"), blank=True)
    telegram_text = models.TextField(_("Текст для Telegram"), blank=True)
    facebook_text = models.TextField(_("Текст для Facebook"), blank=True)
    common_social_text = models.TextField(_("Общий текст для соц.сетей"), blank=True)

    internal_comment = models.TextField(
        _("Внутренний комментарий"),
        blank=True,
        help_text=_("Не отправляется в пост, только для внутреннего использования."),
    )

    send_to_marketplace = models.BooleanField(
        _("Отправлять в list.am/avito?"),
        default=False,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="posts",
        verbose_name=_("Автор"),
    )
    created_at = models.DateTimeField(_("Создан"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлён"), auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Пост")
        verbose_name_plural = _("Посты")

    def __str__(self):
        return self.text[:60] or f"Post #{self.pk}"


class PostAttachment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(
        _("Файл"),
        upload_to=post_attachment_path,
        validators=[validate_post_attachment],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Вложение поста")
        verbose_name_plural = _("Вложения поста")

    def __str__(self):
        return self.file.name


class SalesPost(models.Model):
    """Пост в соц.сетях продажи (list.am/avito и т.п.)."""

    title = models.CharField(_("Заголовок"), max_length=255)
    text = models.TextField(_("Основной текст"))
    price_amd = models.PositiveIntegerField(_("Цена (AMD)"))

    source_post = models.ForeignKey(
        Post,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_posts",
        verbose_name=_("Исходный пост"),
    )
    is_auto_generated = models.BooleanField(_("Создан автоматически"), default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_posts",
        verbose_name=_("Автор"),
    )
    created_at = models.DateTimeField(_("Создан"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлён"), auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Пост в сетях продажи")
        verbose_name_plural = _("Посты в сетях продажи")

    def __str__(self):
        return self.title


class SalesPostAttachment(models.Model):
    sales_post = models.ForeignKey(SalesPost, on_delete=models.CASCADE, related_name="attachments")
    file = models.ImageField(
        _("Файл (JPEG)"),
        upload_to=sales_attachment_path,
        validators=[validate_sales_attachment],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Вложение (продажа)")
        verbose_name_plural = _("Вложения (продажа)")

    def __str__(self):
        return self.file.name
