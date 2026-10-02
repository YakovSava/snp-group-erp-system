"""Deep (content-based) file type detection shared across apps.

Never trusts the filename extension or the browser-supplied Content-Type —
sniffs the actual bytes instead, so renaming a .png to .jpg before upload
does not fool validation.
"""
import magic
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

POST_ATTACHMENT_MIMES = {
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/avif": "avif",
    "image/gif": "gif",
    "video/mp4": "mp4",
    "video/quicktime": "mov",
}

SALES_ATTACHMENT_MIMES = {
    "image/jpeg": "jpeg",
}

CATALOG_IMPORT_MIMES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
}


def sniff_mime(django_file) -> str:
    """Returns the real MIME type of an uploaded file by inspecting its bytes."""
    django_file.seek(0)
    head = django_file.read(4096)
    django_file.seek(0)
    return magic.from_buffer(head, mime=True)


def validate_against(django_file, allowed_mimes: dict, error_message):
    mime = sniff_mime(django_file)
    if mime not in allowed_mimes:
        raise ValidationError(error_message % {"mime": mime})
    return mime


def validate_post_attachment(django_file):
    return validate_against(
        django_file,
        POST_ATTACHMENT_MIMES,
        _("Недопустимый тип файла (%(mime)s). Разрешены: PNG, JPEG, AVIF, GIF, MP4, MOV."),
    )


def validate_sales_attachment(django_file):
    return validate_against(
        django_file,
        SALES_ATTACHMENT_MIMES,
        _("Недопустимый тип файла (%(mime)s). Разрешён только JPEG."),
    )


def validate_catalog_import(django_file):
    return validate_against(
        django_file,
        CATALOG_IMPORT_MIMES,
        _("Недопустимый тип файла (%(mime)s). Разрешён только Excel (.xlsx)."),
    )
