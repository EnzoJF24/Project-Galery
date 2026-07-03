"""Image processing — metadata extraction and thumbnail generation.

Each image is opened once with Pillow to read its metadata and produce a
thumbnail on disk. The original file is never modified or moved: this
tool only ever reads from a client's file server, it never writes to it.
"""

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from gallery.config import THUMBNAIL_MAX_SIZE

logger = logging.getLogger(__name__)


@dataclass
class ProcessedImage:
    """Metadata extracted from a source image, plus its thumbnail's name."""

    thumb_name: str
    width: int
    height: int
    format: str
    size_bytes: int


def thumbnail_filename(project_key: str, rel_path: str) -> str:
    """Derive a collision-free thumbnail filename for an image.

    Naming the thumbnail after the original filename (e.g. "render.jpg")
    would collide the moment two different subfolders of the same project
    both happen to contain a file with that name. Hashing the full
    (project_key, rel_path) pair instead guarantees uniqueness and is
    reproducible, so re-running a scan always derives the same name for
    the same image.
    """
    digest = hashlib.sha1(f"{project_key}/{rel_path}".encode("utf-8")).hexdigest()
    return f"{digest[:16]}.jpg"


def process_image(
    source_path: Path, thumb_output_path: Path
) -> ProcessedImage | None:
    """Read an image's metadata and write its thumbnail to disk.

    Returns None (and logs a warning) instead of raising if the file is
    corrupt or otherwise unreadable — a single bad file must never abort
    the rest of the scan.
    """
    try:
        with Image.open(source_path) as img:
            # img.format is only reliable immediately after opening — it is
            # not preserved by exif_transpose() below, so capture it first.
            image_format = img.format or source_path.suffix.lstrip(".").upper()

            # Some renders carry an EXIF orientation tag; without applying
            # it the thumbnail can come out sideways even though the
            # original displays correctly in other viewers.
            img = ImageOps.exif_transpose(img)
            width, height = img.size

            thumb = img.copy()
            thumb.thumbnail((THUMBNAIL_MAX_SIZE, THUMBNAIL_MAX_SIZE))
            # Thumbnails are normalized to RGB JPEG regardless of the
            # source format, since PNGs may carry an alpha channel that
            # JPEG can't store.
            if thumb.mode != "RGB":
                thumb = thumb.convert("RGB")
            thumb_output_path.parent.mkdir(parents=True, exist_ok=True)
            thumb.save(thumb_output_path, "JPEG", quality=85)

        size_bytes = source_path.stat().st_size
        return ProcessedImage(
            thumb_name=thumb_output_path.name,
            width=width,
            height=height,
            format=image_format,
            size_bytes=size_bytes,
        )
    except (UnidentifiedImageError, OSError) as error:
        logger.warning("Skipping unreadable image %s: %s", source_path, error)
        return None
