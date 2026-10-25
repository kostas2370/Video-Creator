"""Normalize local reference images for multimodal model requests."""

import base64
from io import BytesIO

from PIL import Image, ImageOps


def image_data(reference):
    if not reference:
        return None
    # Normalize file formats and bound encoded payload size for model APIs.
    with Image.open(reference) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail((1536, 1536))
        with BytesIO() as buffer:
            image.save(buffer, format="JPEG", quality=90)
            return base64.b64encode(buffer.getvalue()).decode("ascii")
