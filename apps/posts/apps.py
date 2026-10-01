from django.apps import AppConfig


class PostsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.posts"
    label = "posts"
    verbose_name = "Посты и SMM"

    def ready(self):
        from . import signals  # noqa: F401
