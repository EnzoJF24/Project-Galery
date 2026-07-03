"""Central configuration for Project Gallery.

Every value that other modules need to agree on (which files count as
images, where generated artifacts live, how large a thumbnail should be)
lives here. Nothing below should be hardcoded again anywhere else in the
codebase.
"""

from pathlib import Path

# Image extensions the crawler will pick up, matched case-insensitively.
# Kept intentionally narrow to the formats the spec calls for — add more
# here (e.g. ".webp") rather than special-casing them elsewhere.
VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

# Longest side of a generated thumbnail, in pixels. Aspect ratio is preserved.
THUMBNAIL_MAX_SIZE = 400

# Default locations, relative to the current working directory. Both are
# overridable via CLI flags in scan.py so the tool never assumes a fixed
# layout on disk.
DEFAULT_DB_PATH = Path("gallery.db")
DEFAULT_THUMBNAILS_DIR = Path("thumbnails")
