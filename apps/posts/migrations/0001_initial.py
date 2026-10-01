import apps.core.file_validation
import apps.posts.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Post",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField(verbose_name="Основной текст")),
                ("instagram_text", models.TextField(blank=True, verbose_name="Текст для Instagram")),
                ("telegram_text", models.TextField(blank=True, verbose_name="Текст для Telegram")),
                ("facebook_text", models.TextField(blank=True, verbose_name="Текст для Facebook")),
                ("common_social_text", models.TextField(blank=True, verbose_name="Общий текст для соц.сетей")),
                (
                    "internal_comment",
                    models.TextField(
                        blank=True,
                        help_text="Не отправляется в пост, только для внутреннего использования.",
                        verbose_name="Внутренний комментарий",
                    ),
                ),
                ("send_to_marketplace", models.BooleanField(default=False, verbose_name="Отправлять в list.am/avito?")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлён")),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="posts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Автор",
                    ),
                ),
            ],
            options={
                "verbose_name": "Пост",
                "verbose_name_plural": "Посты",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SalesPost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255, verbose_name="Заголовок")),
                ("text", models.TextField(verbose_name="Основной текст")),
                ("price_amd", models.PositiveIntegerField(verbose_name="Цена (AMD)")),
                ("is_auto_generated", models.BooleanField(default=False, verbose_name="Создан автоматически")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлён")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sales_posts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Автор",
                    ),
                ),
                (
                    "source_post",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sales_posts",
                        to="posts.post",
                        verbose_name="Исходный пост",
                    ),
                ),
            ],
            options={
                "verbose_name": "Пост в сетях продажи",
                "verbose_name_plural": "Посты в сетях продажи",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SalesPostAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "file",
                    models.ImageField(
                        upload_to=apps.posts.models.sales_attachment_path,
                        validators=[apps.core.file_validation.validate_sales_attachment],
                        verbose_name="Файл (JPEG)",
                    ),
                ),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "sales_post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="posts.salespost",
                    ),
                ),
            ],
            options={
                "verbose_name": "Вложение (продажа)",
                "verbose_name_plural": "Вложения (продажа)",
            },
        ),
        migrations.CreateModel(
            name="PostAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "file",
                    models.FileField(
                        upload_to=apps.posts.models.post_attachment_path,
                        validators=[apps.core.file_validation.validate_post_attachment],
                        verbose_name="Файл",
                    ),
                ),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="posts.post",
                    ),
                ),
            ],
            options={
                "verbose_name": "Вложение поста",
                "verbose_name_plural": "Вложения поста",
            },
        ),
    ]
