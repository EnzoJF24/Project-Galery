import pytest

from gallery.crawler import crawl


def test_finds_two_projects(sample_root):
    result = crawl(sample_root)
    project_names = {p.name for p in result.projects}
    assert project_names == {"ProjectA", "ProjectB"}


def test_finds_images_at_any_depth(sample_root):
    result = crawl(sample_root)
    project_a = next(p for p in result.projects if p.name == "ProjectA")
    rel_paths = {img.rel_path for img in project_a.images}
    assert rel_paths == {"cover.jpg", "renders/deep/nested/wall.png"}


def test_ignores_non_image_files(sample_root):
    result = crawl(sample_root)
    all_rel_paths = {
        img.rel_path for project in result.projects for img in project.images
    }
    assert not any(path.endswith(".txt") for path in all_rel_paths)


def test_counts_loose_images_without_indexing_them(sample_root):
    result = crawl(sample_root)
    assert result.loose_image_count == 1
    all_rel_paths = {
        img.rel_path for project in result.projects for img in project.images
    }
    assert "loose_in_root.jpg" not in all_rel_paths


def test_project_key_is_stable_relative_path(sample_root):
    result = crawl(sample_root)
    project_a = next(p for p in result.projects if p.name == "ProjectA")
    # project_key must not depend on the absolute path, only on the
    # folder's position relative to the scan root.
    assert project_a.project_key == "ProjectA"


def test_missing_root_raises(tmp_path):
    with pytest.raises(NotADirectoryError):
        crawl(tmp_path / "does_not_exist")
