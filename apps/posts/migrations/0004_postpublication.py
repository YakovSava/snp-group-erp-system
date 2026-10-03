import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0003_meta_text_and_price"),
    ]

    operations = [
        migrations.CreateModel(
            name="PostPublication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(max_length=20, verbose_name="Платформа")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("success", "Опубликовано"),
                            ("error", "Ошибка"),
                            ("skipped_unconfigured", "Пропущено (нет токена)"),
                        ],
                        max_length=20,
                        verbose_name="Статус",
                    ),
                ),
                ("detail", models.TextField(blank=True, verbose_name="Подробности")),
                ("external_url", models.URLField(blank=True, verbose_name="Ссылка на публикацию")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Отправлено")),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="publications",
                        to="posts.post",
                    ),
                ),
            ],
            options={
                "verbose_name": "Публикация в соц.сети",
                "verbose_name_plural": "Публикации в соц.сетях",
                "ordering": ["-created_at"],
            },
        ),
    ]
