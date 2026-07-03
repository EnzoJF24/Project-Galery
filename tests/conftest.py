"""Shared pytest fixtures: build small, disposable file trees on disk.

Building real folders (instead of mocking the filesystem) keeps the
crawler and processor tests honest about how os.walk and Pillow actually
behave.
"""

import pytest
from PIL import Image


def _write_fake_image(path, size=(20, 20), color=(120, 160, 200)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


@pytest.fixture
def sample_root(tmp_path):
    """A scan root with two projects, nested renders, and one loose image.

    Layout::

        root/
            ProjectA/
                cover.jpg
                renders/deep/nested/wall.png
            ProjectB/
                shot.jpeg
            loose_in_root.jpg      <- not inside any project folder
            notes.txt              <- not an image, must be ignored
    """
    root = tmp_path / "root"

    _write_fake_image(root / "ProjectA" / "cover.jpg")
    _write_fake_image(root / "ProjectA" / "renders" / "deep" / "nested" / "wall.png")
    _write_fake_image(root / "ProjectB" / "shot.jpeg")
    _write_fake_image(root / "loose_in_root.jpg")
    (root / "notes.txt").parent.mkdir(parents=True, exist_ok=True)
    (root / "notes.txt").write_text("not an image")

    return root
