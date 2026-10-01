import io

import cairosvg
import pillow_avif  # noqa: F401 - registers the AVIF plugin with Pillow on import
import pillow_heif
from PIL import Image
from psd_tools import PSDImage

pillow_heif.register_heif_opener()

PIL_TARGET_FORMATS = {"png": "PNG", "jpg": "JPEG", "jpeg": "JPEG", "webp": "WEBP"}


def _load_as_pil_image(django_file, source_format):
    django_file.seek(0)
    if source_format == "svg":
        png_bytes = cairosvg.svg2png(bytestring=django_file.read())
        return Image.open(io.BytesIO(png_bytes))
    if source_format == "psd":
        psd = PSDImage.open(django_file)
        return psd.composite()
    return Image.open(django_file)


def convert_image(django_file, source_format, target_format):
    """Converts an uploaded image (file-like, e.g. a Django FieldFile) to
    target_format ("png" | "jpg"/"jpeg" | "webp") and returns the result bytes.
    """
    pil_format = PIL_TARGET_FORMATS.get(target_format.lower())
    if pil_format is None:
        raise ValueError(f"Unsupported target format: {target_format}")

    image = _load_as_pil_image(django_file, source_format)
    image.load()

    if pil_format == "JPEG" and image.mode in ("RGBA", "LA", "P"):
        rgba_image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(rgba_image, mask=rgba_image.split()[-1])
        image = background
    elif pil_format != "JPEG" and image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")

    # GIFs/animated sources: keep only the first frame for a static target.
    buffer = io.BytesIO()
    image.save(buffer, format=pil_format)
    return buffer.getvalue()
