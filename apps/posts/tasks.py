from celery import shared_task
from django.core.files.base import ContentFile

from apps.core import ai_client
from apps.utilities.services import detect, image

from .models import Post, PostTranslation, SalesPost, SalesPostAttachment

AUTO_SALES_POST_TITLE = "Test Title for card on list.am/avito"
AUTO_SALES_POST_PRICE_AMD = 10


@shared_task
def create_sales_post_from_post(post_id):
    """Mirrors a Post flagged "Отправлять в list.am/avito?" into a SalesPost,
    converting any image attachments to JPEG (the only format SalesPost
    accepts) via the same conversion engine the Utilities section uses.
    """
    try:
        post = Post.objects.prefetch_related("attachments").get(pk=post_id)
    except Post.DoesNotExist:
        return

    sales_post = SalesPost.objects.create(
        title=AUTO_SALES_POST_TITLE,
        text=post.text,
        price_amd=AUTO_SALES_POST_PRICE_AMD,
        source_post=post,
        is_auto_generated=True,
        created_by=post.created_by,
    )

    for attachment in post.attachments.all():
        source_format, mime = detect.detect_image_format(attachment.file)
        if source_format is None:
            continue  # video/other non-image attachments have no JPEG equivalent here

        jpeg_bytes = image.convert_image(attachment.file, source_format, "jpg")
        filename = f"{attachment.pk}.jpg"
        SalesPostAttachment.objects.create(
            sales_post=sales_post,
            file=ContentFile(jpeg_bytes, name=filename),
        )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def localize_post(self, post_id):
    """Translates Post.text into EN and HY via ai-assistant and stores the
    results as PostTranslation rows. EN gets a parenthetical USD equivalent
    next to any AMD amount (international-audience framing); HY is left in
    AMD (local audience, no conversion needed).
    """
    try:
        post = Post.objects.get(pk=post_id)
    except Post.DoesNotExist:
        return

    try:
        en_text = ai_client.translate(post.text, "en", annotate_amd_with_usd=True)
        hy_text = ai_client.translate(post.text, "hy", annotate_amd_with_usd=False)
    except Exception as exc:
        raise self.retry(exc=exc)

    PostTranslation.objects.update_or_create(
        post=post, language=PostTranslation.LANGUAGE_EN, defaults={"text": en_text}
    )
    PostTranslation.objects.update_or_create(
        post=post, language=PostTranslation.LANGUAGE_HY, defaults={"text": hy_text}
    )
