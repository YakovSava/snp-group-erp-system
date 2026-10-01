import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PostTranslation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "language",
                    models.CharField(
                        choices=[("en", "Английский"), ("hy", "Армянский")],
                        max_length=5,
                        verbose_name="Язык",
                    ),
                ),
                ("text", models.TextField(verbose_name="Текст")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="posts.post",
                    ),
                ),
            ],
            options={
                "verbose_name": "Перевод поста",
                "verbose_name_plural": "Переводы поста",
            },
        ),
        migrations.AddConstraint(
            model_name="posttranslation",
            constraint=models.UniqueConstraint(
                fields=("post", "language"), name="unique_post_translation_language"
            ),
        ),
    ]
