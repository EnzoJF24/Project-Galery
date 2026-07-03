"""Tests for the property the whole project hinges on: re-running a scan
must never reprocess what it already indexed, but must still catch
genuinely new images — including ones dropped into an already-known
project, and ones left over from a scan that died partway through.
"""

from gallery import index
from scan import run_scan


def _image_count(db_path):
    conn = index.get_connection(db_path)
    row = conn.execute("SELECT COUNT(*) AS n FROM images").fetchone()
    conn.close()
    return row["n"]


def test_rescanning_unchanged_tree_indexes_nothing_new(sample_root, tmp_path):
    db_path = tmp_path / "gallery.db"
    thumbs_dir = tmp_path / "thumbnails"

    run_scan(sample_root, db_path, thumbs_dir)
    first_count = _image_count(db_path)

    run_scan(sample_root, db_path, thumbs_dir)
    second_count = _image_count(db_path)

    assert first_count == 3  # cover.jpg, wall.png, shot.jpeg from conftest
    assert second_count == first_count


def test_new_image_in_existing_project_is_detected(sample_root, tmp_path):
    db_path = tmp_path / "gallery.db"
    thumbs_dir = tmp_path / "thumbnails"

    run_scan(sample_root, db_path, thumbs_dir)

    from PIL import Image

    Image.new("RGB", (300, 300), (1, 1, 1)).save(sample_root / "ProjectB" / "extra.jpg")

    run_scan(sample_root, db_path, thumbs_dir)

    conn = index.get_connection(db_path)
    project = index.get_project_by_key(conn, "ProjectB")
    rel_paths = index.get_indexed_rel_paths(conn, project["id"])
    conn.close()

    assert "extra.jpg" in rel_paths
    assert _image_count(db_path) == 4  # 3 original + the 1 new one


def test_project_key_survives_root_move(sample_root, tmp_path):
    """A project's identity must not depend on the scan root's absolute
    path, so moving the whole tree elsewhere should not make everything
    look "new" again."""
    db_path = tmp_path / "gallery.db"
    thumbs_dir = tmp_path / "thumbnails"
    run_scan(sample_root, db_path, thumbs_dir)

    moved_root = tmp_path / "moved_root"
    sample_root.rename(moved_root)

    run_scan(moved_root, db_path, thumbs_dir)

    assert _image_count(db_path) == 3  # still 3, nothing reprocessed as "new"


def test_interrupted_scan_resumes_without_duplicating(sample_root, tmp_path):
    """Simulate a scan that died after indexing only one image of a
    project: manually seed that partial state, then run a full scan and
    confirm the rest gets picked up with no duplicates."""
    db_path = tmp_path / "gallery.db"
    thumbs_dir = tmp_path / "thumbnails"

    conn = index.get_connection(db_path)
    project_id = index.get_or_create_project(conn, "ProjectA", "ProjectA", "2026-01-01T00:00:00")
    index.insert_image(conn, project_id, "cover.jpg", "seed.jpg", 20, 20, "JPEG", 100)
    # Deliberately not marking scan_completed=1, mimicking a crash mid-project.
    conn.commit()
    conn.close()

    run_scan(sample_root, db_path, thumbs_dir)

    conn = index.get_connection(db_path)
    project = index.get_project_by_key(conn, "ProjectA")
    rel_paths = index.get_indexed_rel_paths(conn, project["id"])
    conn.close()

    assert rel_paths == {"cover.jpg", "renders/deep/nested/wall.png"}
