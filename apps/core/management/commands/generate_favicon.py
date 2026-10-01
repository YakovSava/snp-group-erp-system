from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image

SOURCE_LOGO = "images/branding/logo-mark.png"
OUTPUT_NAME = "images/favicon.ico"
ICON_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64)]


class Command(BaseCommand):
    """Builds static/images/favicon.ico from the brand logo mark.

    The brief references brandbook/favicon.ico, but no such file actually
    ships in the brandbook — this derives one from the logo instead so the
    build never depends on a file that doesn't exist.
    """

    help = "Generate favicon.ico from the brand logo mark."

    def handle(self, *args, **options):
        source_path = Path(settings.BASE_DIR) / "static" / SOURCE_LOGO
        if not source_path.exists():
            self.stderr.write(self.style.WARNING(f"Logo source not found at {source_path}, skipping favicon generation."))
            return

        output_path = Path(settings.BASE_DIR) / "static" / OUTPUT_NAME
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logo = Image.open(source_path).convert("RGBA")

        side = max(logo.width, logo.height)
        padded_side = int(side * 1.3)
        canvas = Image.new("RGBA", (padded_side, padded_side), (0, 0, 0, 0))
        offset = ((padded_side - logo.width) // 2, (padded_side - logo.height) // 2)
        canvas.paste(logo, offset, logo)

        canvas.save(output_path, format="ICO", sizes=ICON_SIZES)
        self.stdout.write(self.style.SUCCESS(f"Favicon written to {output_path}"))
