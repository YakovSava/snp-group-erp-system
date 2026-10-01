from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.file_validation import validate_post_attachment, validate_sales_attachment

from .models import Post, SalesPost


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultiFileInput(attrs={"multiple": True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data]
        return single_file_clean(data, initial)


class PostForm(forms.ModelForm):
    """Public creation form.

    Deliberately excludes instagram_text / telegram_text / facebook_text /
    common_social_text — those are admin-only fields per the brief.
    """

    attachments = MultiFileField(
        required=False,
        label=_("Приложения"),
        help_text=_("PNG, JPEG, AVIF, GIF, MP4, MOV."),
        validators=[validate_post_attachment],
    )

    class Meta:
        model = Post
        fields = ["text", "internal_comment", "send_to_marketplace"]
        widgets = {
            "text": forms.Textarea(attrs={"rows": 5}),
            "internal_comment": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "send_to_marketplace": _("Отправлять в list.am/avito?"),
        }


class SalesPostForm(forms.ModelForm):
    attachments = MultiFileField(
        required=False,
        label=_("Приложения (только JPG)"),
        validators=[validate_sales_attachment],
    )

    class Meta:
        model = SalesPost
        fields = ["title", "text", "price_amd"]
        widgets = {
            "text": forms.Textarea(attrs={"rows": 5}),
        }
        labels = {
            "price_amd": _("Цена (драм)"),
        }
