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

    CURRENCY_AMD = "AMD"
    CURRENCY_RUB = "RUB"
    CURRENCY_USD = "USD"
    CURRENCY_CHOICES = [
        (CURRENCY_AMD, _("AMD (драм)")),
        (CURRENCY_RUB, _("RUB (рубль)")),
        (CURRENCY_USD, _("USD (доллар)")),
    ]

    text = models.TextField(_("Основной текст"))

    meta_text = models.TextField(
        _("Текст для Facebook/Instagram (Meta)"),
        blank=True,
        help_text=_("Публикуется без изменений в Facebook и Instagram."),
    )
    telegram_text = models.TextField(_("Текст для Telegram"), blank=True)
    common_social_text = models.TextField(_("Общий текст для соц.сетей"), blank=True)

    price_amount = models.DecimalField(
        _("Цена"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Обязательна, если пост попадёт в соц.сети или на list.am/avito."),
    )
    price_currency = models.CharField(
        _("Валюта цены"),
        max_length=3,
        choices=CURRENCY_CHOICES,
        default=CURRENCY_AMD,
        blank=True,
    )

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


class PostTranslation(models.Model):
    """AI-generated localized copy of Post.text, created automatically on
    Post creation by apps.posts.tasks.localize_post. 'ru' isn't stored here
    since it's the source language (Post.text itself).
    """

    LANGUAGE_EN = "en"
    LANGUAGE_HY = "hy"
    LANGUAGE_CHOICES = [
        (LANGUAGE_EN, _("Английский")),
        (LANGUAGE_HY, _("Армянский")),
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="translations")
    language = models.CharField(_("Язык"), max_length=5, choices=LANGUAGE_CHOICES)
    text = models.TextField(_("Текст"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["post", "language"], name="unique_post_translation_language"),
        ]
        verbose_name = _("Перевод поста")
        verbose_name_plural = _("Переводы поста")

    def __str__(self):
        return f"{self.post_id} [{self.language}]"


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
