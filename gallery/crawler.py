"""Filesystem crawler — discovers projects and images under a scan root.

A "project" is any top-level folder directly under the root. Everything
below that folder is searched recursively for image files, at whatever
depth they happen to live at: this tool makes no assumption about
subfolder naming ("renders", "renderings", "images"...) or nesting depth,
since that structure varies project to project on a real file server.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from gallery.config import VALID_IMAGE_EXTENSIONS


@dataclass
class DiscoveredImage:
    """A single image found under a project, with a stable relative path."""

    rel_path: str
    absolute_path: Path


@dataclass
class DiscoveredProject:
    """A top-level folder under the scan root, with its images."""

    project_key: str
    name: str
    absolute_path: Path
    images: list[DiscoveredImage]


@dataclass
class CrawlResult:
    """Everything found in one pass over the scan root."""

    projects: list[DiscoveredProject]
    loose_image_count: int


def _is_image(filename: str) -> bool:
    return Path(filename).suffix.lower() in VALID_IMAGE_EXTENSIONS


def _find_images(directory: Path) -> list[DiscoveredImage]:
    """Recursively collect images under ``directory``, at any depth.

    Paths that can't be listed (permission errors, broken links) are
    skipped rather than aborting the whole crawl — one unreadable folder
    should not take down the scan for every other project.
    """
    images: list[DiscoveredImage] = []
    for current_dir, _subdirs, files in os.walk(directory, onerror=lambda e: None):
        for filename in files:
            if _is_image(filename):
                absolute_path = Path(current_dir) / filename
                rel_path = str(absolute_path.relative_to(directory).as_posix())
                images.append(DiscoveredImage(rel_path=rel_path, absolute_path=absolute_path))
    return images


def crawl(root: Path) -> CrawlResult:
    """Walk ``root`` and return every project and image found beneath it.

    Images sitting loose directly in ``root`` (not inside any project
    folder) are deliberately not indexed — the tool's unit of
    organization is the project, and a file with no project can't be
    grouped meaningfully in the gallery. They are counted instead, so the
    scan CLI and the viewer can both surface that they exist somewhere
    the user should look at manually.
    """
    if not root.is_dir():
        raise NotADirectoryError(f"Scan root does not exist or is not a directory: {root}")

    projects: list[DiscoveredProject] = []
    loose_image_count = 0

    for entry in sorted(root.iterdir()):
        if entry.is_dir():
            images = _find_images(entry)
            projects.append(
                DiscoveredProject(
                    project_key=entry.name,
                    name=entry.name,
                    absolute_path=entry,
                    images=images,
                )
            )
        elif entry.is_file() and _is_image(entry.name):
            loose_image_count += 1

    return CrawlResult(projects=projects, loose_image_count=loose_image_count)
