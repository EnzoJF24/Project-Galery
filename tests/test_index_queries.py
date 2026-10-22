"""Tests for the read queries the viewer is built on: library stats,
per-folder breakdowns, folder filtering, sorting and detail-view stepping.
"""

from gallery import index
from scan import run_scan


def _scanned_conn(sample_root, tmp_path):
    db_path = tmp_path / "gallery.db"
    run_scan(sample_root, db_path, tmp_path / "thumbnails")
    return index.get_connection(db_path)


def test_library_stats_summarize_the_whole_index(sample_root, tmp_path):
    conn = _scanned_conn(sample_root, tmp_path)
    stats = index.get_library_stats(conn)

    assert stats["project_count"] == 2
    assert stats["image_count"] == 3
    assert stats["total_bytes"] > 0
    # ProjectA/"" + ProjectA/renders/deep/nested + ProjectB/""
    assert stats["folder_count"] == 3
    assert stats["max_depth"] == 3  # renders/deep/nested/wall.png


def test_project_folders_lists_where_images_were_found(sample_root, tmp_path):
    conn = _scanned_conn(sample_root, tmp_path)
    project = index.get_project_by_key(conn, "ProjectA")

    folders = {row["folder"]: row["image_count"] for row in index.list_project_folders(conn, project["id"])}

    assert folders == {"": 1, "renders/deep/nested": 1}


def test_folder_filter_restricts_listing_and_count(sample_root, tmp_path):
    conn = _scanned_conn(sample_root, tmp_path)
    project_id = index.get_project_by_key(conn, "ProjectA")["id"]

    nested = index.list_images(conn, project_id, folder="renders/deep/nested")
    top_level = index.list_images(conn, project_id, folder="")

    assert [row["rel_path"] for row in nested] == ["renders/deep/nested/wall.png"]
    assert [row["rel_path"] for row in top_level] == ["cover.jpg"]
    assert index.count_images(conn, project_id, folder="renders/deep/nested") == 1
    assert index.count_images(conn, project_id) == 2


def test_projects_can_be_sorted_by_image_count(sample_root, tmp_path):
    conn = _scanned_conn(sample_root, tmp_path)

    by_images = [row["name"] for row in index.list_projects(conn, sort="images")]

    assert by_images == ["ProjectA", "ProjectB"]


def test_image_neighbors_follow_grid_order(sample_root, tmp_path):
    conn = _scanned_conn(sample_root, tmp_path)
    project_id = index.get_project_by_key(conn, "ProjectA")["id"]
    first, second = index.list_images(conn, project_id)

    at_first = index.get_image_neighbors(conn, project_id, first["rel_path"])
    at_second = index.get_image_neighbors(conn, project_id, second["rel_path"])

    assert (at_first["prev_id"], at_first["next_id"], at_first["position"]) == (None, second["id"], 1)
    assert (at_second["prev_id"], at_second["next_id"], at_second["position"]) == (first["id"], None, 2)
