from celery import shared_task
from django.core.files.base import ContentFile

from apps.core import ai_client
from apps.utilities.services import detect, image

from .models import Post, PostTranslation, SalesPost, SalesPostAttachment

FALLBACK_SALES_POST_TITLE = "Товар SNP (требуется уточнить заголовок)"


def _price_to_amd(price_amount, price_currency) -> int:
    if price_currency == Post.CURRENCY_AMD:
        return round(price_amount)
    converted = ai_client.convert_currency(float(price_amount), price_currency, Post.CURRENCY_AMD)
    return round(converted)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def create_sales_post_from_post(self, post_id):
    """Mirrors a Post flagged "Отправлять в list.am/avito?" into a SalesPost,
    converting any image attachments to JPEG (the only format SalesPost
    accepts) via the same conversion engine the Utilities section uses.

    Price comes from the Post itself (entered by the employee, never guessed
    by AI); only the card title is AI-generated, from the post's text.
    """
    try:
        post = Post.objects.prefetch_related("attachments").get(pk=post_id)
    except Post.DoesNotExist:
        return

    if not post.price_amount:
        # Shouldn't happen — PostForm and the SMM tool both require a price
        # whenever send_to_marketplace is set. No safe price to fall back to,
        # so skip rather than publish a SalesPost with a fabricated one.
        return

    try:
        price_amd = _price_to_amd(post.price_amount, post.price_currency)
        title = ai_client.generate_sales_title(post.text) or FALLBACK_SALES_POST_TITLE
    except Exception as exc:
        raise self.retry(exc=exc)

    sales_post = SalesPost.objects.create(
        title=title[:255],
        text=post.text,
        price_amd=price_amd,
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
