from PIL import Image

from gallery.processor import process_image, thumbnail_filename


def test_process_image_extracts_metadata_and_writes_thumbnail(tmp_path):
    source = tmp_path / "render.jpg"
    Image.new("RGB", (800, 600), (10, 20, 30)).save(source)
    thumb_path = tmp_path / "thumbnails" / "abc123.jpg"

    result = process_image(source, thumb_path)

    assert result is not None
    assert result.width == 800
    assert result.height == 600
    assert result.format == "JPEG"
    assert result.size_bytes > 0
    assert thumb_path.exists()


def test_thumbnail_is_resized_and_preserves_aspect_ratio(tmp_path):
    source = tmp_path / "wide.png"
    Image.new("RGB", (2000, 1000), (0, 0, 0)).save(source)
    thumb_path = tmp_path / "thumbnails" / "wide_thumb.jpg"

    process_image(source, thumb_path)

    with Image.open(thumb_path) as thumb:
        assert max(thumb.size) <= 400
        assert thumb.size[0] / thumb.size[1] == 2.0  # original was 2:1


def test_corrupt_image_returns_none_instead_of_raising(tmp_path):
    source = tmp_path / "broken.jpg"
    source.write_bytes(b"this is not a valid image file")
    thumb_path = tmp_path / "thumbnails" / "broken.jpg"

    result = process_image(source, thumb_path)

    assert result is None
    assert not thumb_path.exists()


def test_thumbnail_filename_has_no_collisions_across_subfolders():
    name_a = thumbnail_filename("ProjectA", "renders/room1/shot.jpg")
    name_b = thumbnail_filename("ProjectA", "renders/room2/shot.jpg")
    assert name_a != name_b


def test_thumbnail_filename_is_reproducible():
    first = thumbnail_filename("ProjectA", "renders/shot.jpg")
    second = thumbnail_filename("ProjectA", "renders/shot.jpg")
    assert first == second
