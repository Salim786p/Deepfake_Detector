import hashlib
import io
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import get_settings


ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}

PIL_FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
}


@dataclass(slots=True)
class PreparedImage:
    original_bytes: bytes
    original_mime_type: str
    analysis_bytes: bytes
    analysis_mime_type: str
    filename: str
    width: int
    height: int
    sha256: str


class ImagePreparationError(ValueError):
    pass


async def download_image_from_url(image_url: str) -> Tuple[bytes, Optional[str], str]:
    settings = get_settings()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36"
        )
    }

    timeout = httpx.Timeout(settings.request_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        response = await client.get(image_url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower() or None
        content = response.content
        if len(content) > settings.max_download_bytes:
            raise ImagePreparationError("Image exceeds the maximum allowed size of 10 MB.")

        parsed = urlparse(str(image_url))
        filename = parsed.path.rsplit("/", 1)[-1] or "image"
        return content, content_type, filename


def prepare_image(
    image_bytes: bytes,
    *,
    content_type: Optional[str] = None,
    filename: str = "image",
) -> PreparedImage:
    if not image_bytes:
        raise ImagePreparationError("No image bytes were provided.")

    settings = get_settings()
    if len(image_bytes) > settings.max_download_bytes:
        raise ImagePreparationError("Image exceeds the maximum allowed size of 10 MB.")

    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image = ImageOps.exif_transpose(image)
            image.load()
            width, height = image.size
            detected_format = (image.format or "").upper()
            detected_mime = PIL_FORMAT_TO_MIME.get(detected_format)
            resolved_mime = content_type if content_type in ALLOWED_MIME_TYPES else detected_mime
            if resolved_mime not in ALLOWED_MIME_TYPES:
                raise ImagePreparationError(
                    "Unsupported image format. Use JPEG, PNG, WebP, or GIF."
                )

            analysis_image = image.convert("RGB")
            analysis_image.thumbnail(
                (settings.max_image_dimension, settings.max_image_dimension),
                Image.Resampling.LANCZOS,
            )

            output = io.BytesIO()
            analysis_image.save(output, format="JPEG", quality=92, optimize=True)
            analysis_bytes = output.getvalue()

    except UnidentifiedImageError as exc:
        raise ImagePreparationError("The provided file is not a valid image.") from exc
    except OSError as exc:
        raise ImagePreparationError("The image could not be processed.") from exc

    safe_filename = filename if "." in filename else f"{filename}.jpg"
    if len(safe_filename) > 120:
        stem, _, suffix = safe_filename.rpartition(".")
        safe_filename = f"{stem[:100]}.{suffix or 'jpg'}"

    return PreparedImage(
        original_bytes=image_bytes,
        original_mime_type=resolved_mime or "image/jpeg",
        analysis_bytes=analysis_bytes,
        analysis_mime_type="image/jpeg",
        filename=safe_filename,
        width=width,
        height=height,
        sha256=hashlib.sha256(image_bytes).hexdigest(),
    )
