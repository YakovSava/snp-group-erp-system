import django.dispatch
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Post, SalesPost

# Both currently no-op — reserved for other ESB components to hook into later.
post_created = django.dispatch.Signal()
sales_post_created = django.dispatch.Signal()


@receiver(post_save, sender=Post)
def handle_post_saved(sender, instance, created, **kwargs):
    if not created:
        return

    post_created.send(sender=Post, post=instance)

    if instance.send_to_marketplace:
        from .tasks import create_sales_post_from_post

        # Deferred to transaction commit: the view creates PostAttachments
        # right after saving the Post, in the same atomic block — queuing
        # the task immediately would race the Celery worker against that
        # and could create the SalesPost before any attachments exist.
        transaction.on_commit(lambda: create_sales_post_from_post.delay(instance.pk))


@receiver(post_save, sender=SalesPost)
def handle_sales_post_saved(sender, instance, created, **kwargs):
    if created:
        sales_post_created.send(sender=SalesPost, sales_post=instance)
