"""Tests for the UI's formatting helpers and HTML escaping.

Folder and file names come straight from the scanned server, so the
escaping test matters: a folder named like an HTML tag must render as
text, never as markup.
"""

from datetime import datetime, timedelta, timezone

from gallery.ui import components


def test_format_bytes_picks_a_readable_unit():
    assert components.format_bytes(512) == "512 B"
    assert components.format_bytes(980 * 1024) == "980 KB"
    assert components.format_bytes(int(4.2 * 1024 * 1024)) == "4.2 MB"
    assert components.format_bytes(3 * 1024**3) == "3.0 GB"


def test_relative_time_switches_to_a_date_after_a_day():
    now = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)

    assert components.format_relative_time((now - timedelta(seconds=20)).isoformat(), now) == "just now"
    assert components.format_relative_time((now - timedelta(minutes=5)).isoformat(), now) == "5 min ago"
    assert components.format_relative_time((now - timedelta(hours=3)).isoformat(), now) == "3 h ago"
    assert components.format_relative_time("2026-07-04T09:00:00+00:00", now) == "Jul 4, 2026"


def test_untrusted_names_are_escaped_in_cards():
    html = components.image_card_html("data:,", "<script>x</script>.jpg", "<b>renders</b>", 10, 10)

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;b&gt;renders&lt;/b&gt;" in html


def test_project_card_uses_mosaic_only_with_three_thumbnails():
    with_three = components.project_card_html("P", 12, 3, 1024, ["a", "b", "c"])
    with_one = components.project_card_html("P", 1, 1, 1024, ["a"])

    assert "pg-mosaic" in with_three
    assert "pg-mosaic" not in with_one
    assert "1</b> render<" in with_one
