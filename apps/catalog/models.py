from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class CatalogItem(models.Model):
    """Одна позиция в каталоге товаров.

    article is intentionally a text field, not numeric: supplier article
    codes are never normalized across price lists (letters, dots, dashes,
    mixed case all show up), so anything meant to be matched/searched as
    text must be stored as text.
    """

    title = models.CharField(_("Заголовок"), max_length=500)
    article = models.CharField(_("Артикул"), max_length=255, blank=True, db_index=True)

    amount_amd = models.DecimalField(_("Цена, AMD"), max_digits=12, decimal_places=2, null=True, blank=True)
    amount_rub = models.DecimalField(_("Цена, RUB"), max_digits=12, decimal_places=2, null=True, blank=True)
    amount_usd = models.DecimalField(_("Цена, USD"), max_digits=12, decimal_places=2, null=True, blank=True)

    description = models.TextField(_("Описание"), blank=True)
    supplier = models.TextField(_("Поставщик"), blank=True)
    comment = models.TextField(_("Комментарии"), blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="catalog_items",
        verbose_name=_("Добавил"),
    )
    created_at = models.DateTimeField(_("Создан"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлён"), auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = _("Позиция каталога")
        verbose_name_plural = _("Каталог")

    def __str__(self):
        return self.title or self.article or f"CatalogItem #{self.pk}"
