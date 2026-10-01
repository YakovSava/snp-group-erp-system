import apps.utilities.models
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
            name="ConversionHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.TextField(verbose_name="Что сделал")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="conversion_history",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "История",
                "verbose_name_plural": "История",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ConversionJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "kind",
                    models.CharField(
                        choices=[("image", "Фото"), ("video", "Видео"), ("document", "Файл")],
                        max_length=20,
                    ),
                ),
                ("source_file", models.FileField(upload_to=apps.utilities.models.conversion_source_path)),
                ("detected_source_format", models.CharField(blank=True, max_length=20)),
                ("target_format", models.CharField(max_length=20)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "В очереди"),
                            ("processing", "Обрабатывается"),
                            ("done", "Готово"),
                            ("failed", "Ошибка"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("error_message", models.TextField(blank=True)),
                (
                    "result_file",
                    models.FileField(blank=True, null=True, upload_to=apps.utilities.models.conversion_result_path),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conversion_jobs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Задача конвертации",
                "verbose_name_plural": "Задачи конвертации",
                "ordering": ["-created_at"],
            },
        ),
    ]
