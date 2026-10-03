from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.core.file_validation import validate_catalog_import

from .models import CatalogItem
from .services.excel import SINGLE_VALUE_FIELDS

COLUMN_FIELD_CHOICES = [
    ("ignore", _("— Пропустить —")),
    ("title", _("Заголовок")),
    ("article", _("Артикул")),
    ("amount_amd", _("Цена, AMD")),
    ("amount_rub", _("Цена, RUB")),
    ("amount_usd", _("Цена, USD")),
    ("description", _("Описание")),
    ("supplier", _("Поставщик")),
    ("comment", _("Комментарии")),
]

SEARCH_FIELD_CHOICES = [
    ("all", _("Везде")),
    ("title", _("Заголовок")),
    ("price", _("Цена")),
    ("comment", _("Комментарий")),
]


class CatalogImportUploadForm(forms.Form):
    source_file = forms.FileField(label=_("Excel-файл (.xlsx)"), validators=[validate_catalog_import])

    def clean_source_file(self):
        uploaded = self.cleaned_data["source_file"]
        if uploaded.size > settings.CATALOG_IMPORT_MAX_UPLOAD_SIZE:
            limit_mb = settings.CATALOG_IMPORT_MAX_UPLOAD_SIZE // (1024 * 1024)
            raise ValidationError(_("Файл слишком большой (максимум %(limit)s МБ).") % {"limit": limit_mb})
        return uploaded


class CatalogMappingForm(forms.Form):
    """One field per spreadsheet column (column_0, column_1, ...), built
    dynamically since the column count depends on the uploaded file —
    pre-filled from the AI's suggestion, always reviewed/correctable by the
    employee before anything is written to the database.
    """

    amount_rub_markup_percent = forms.DecimalField(
        label=_("Наценка для RUB, % (если в файле нет столбца с ценой в рублях)"),
        required=False,
        max_digits=6,
        decimal_places=2,
    )
    amount_usd_markup_percent = forms.DecimalField(
        label=_("Наценка для USD, % (если в файле нет столбца с ценой в долларах)"),
        required=False,
        max_digits=6,
        decimal_places=2,
    )

    def __init__(self, *args, headers=None, initial_column_fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers = headers or []
        initial_column_fields = initial_column_fields or []
        for idx, header in enumerate(self.headers):
            initial = initial_column_fields[idx] if idx < len(initial_column_fields) else "comment"
            self.fields[f"column_{idx}"] = forms.ChoiceField(
                label=header or _("Столбец %(index)s") % {"index": idx + 1},
                choices=COLUMN_FIELD_CHOICES,
                initial=initial,
                required=True,
            )

    def clean(self):
        cleaned_data = super().clean()
        seen = {}
        for idx in range(len(self.headers)):
            field = cleaned_data.get(f"column_{idx}")
            if field in SINGLE_VALUE_FIELDS and field in seen:
                self.add_error(
                    f"column_{idx}",
                    _("Это поле уже назначено столбцу %(index)s — выберите другое значение.")
                    % {"index": seen[field] + 1},
                )
            elif field in SINGLE_VALUE_FIELDS:
                seen[field] = idx
        return cleaned_data

    def column_fields(self) -> list[str]:
        return [self.cleaned_data[f"column_{idx}"] for idx in range(len(self.headers))]

    def column_rows(self):
        """(header, bound_field) pairs for straightforward template rendering."""
        return [(header, self[f"column_{idx}"]) for idx, header in enumerate(self.headers)]


class CatalogItemForm(forms.ModelForm):
    class Meta:
        model = CatalogItem
        fields = ["title", "article", "amount_amd", "amount_rub", "amount_usd", "description", "supplier", "comment"]


class CatalogSearchForm(forms.Form):
    q = forms.CharField(label=_("Поиск"), required=False)
    field = forms.ChoiceField(label=_("По полю"), choices=SEARCH_FIELD_CHOICES, required=False, initial="all")
