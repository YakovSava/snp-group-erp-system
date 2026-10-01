from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

IMAGE_TARGET_CHOICES = [("png", "PNG"), ("jpg", "JPG"), ("webp", "WEBP")]
VIDEO_TARGET_CHOICES = [("mp4", "MP4"), ("webm", "WEBM")]
DOCUMENT_TARGET_CHOICES = [
    ("docx", "DOCX"),
    ("xlsx", "XLSX"),
    ("txt", "TXT"),
    ("csv", "CSV"),
    ("pptx", "PPTX"),
    ("pdf", "PDF"),
]


class BaseConversionForm(forms.Form):
    size_limit_key = None

    source_file = forms.FileField(label=_("Файл"))
    target_format = forms.ChoiceField(label=_("Конвертировать в"))

    def clean_source_file(self):
        uploaded = self.cleaned_data["source_file"]
        limit = settings.CONVERSION_MAX_UPLOAD_SIZES[self.size_limit_key]
        if uploaded.size > limit:
            raise ValidationError(
                _("Файл слишком большой (максимум %(limit)s МБ).") % {"limit": limit // (1024 * 1024)}
            )
        return uploaded


class PhotoConversionForm(BaseConversionForm):
    size_limit_key = "image"
    target_format = forms.ChoiceField(label=_("Конвертировать в"), choices=IMAGE_TARGET_CHOICES)


class VideoConversionForm(BaseConversionForm):
    size_limit_key = "video"
    target_format = forms.ChoiceField(label=_("Конвертировать в"), choices=VIDEO_TARGET_CHOICES)


class DocumentConversionForm(BaseConversionForm):
    size_limit_key = "document"
    target_format = forms.ChoiceField(label=_("Конвертировать в"), choices=DOCUMENT_TARGET_CHOICES)
