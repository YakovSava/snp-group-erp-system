"""Image pre-processing before any call to the AI gateway.

Testing against the live gateway (ai.tanakatatsuki.dev) showed its image
endpoints (/v1/images/edits, vision input on /v1/chat/completions) are
unreliable — NOT because of a clean payload-size cutoff (the exact same
~15KB image returned 520, 502, then 520 again on three retries, while an
~18KB image succeeded once), but because the backend itself is flaky under
load. Keeping uploads reasonably small is still good practice (bandwidth,
cost, and a smaller request is simply less likely to hit a slow/overloaded
path), but the real fix is retrying (see llm_client.with_retries) — this
module only handles the "keep it reasonably sized" half.
"""
import io

from PIL import Image

MAX_DIMENSION = 1280
JPEG_QUALITY = 82


def prepare_image_for_api(data: bytes) -> bytes:
    image = Image.open(io.BytesIO(data))
    image = image.convert("RGB")

    if max(image.size) > MAX_DIMENSION:
        image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY)
    return buffer.getvalue()
