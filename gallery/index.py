"""SQLite index — the single source of truth for Project Gallery.

The scan pipeline (crawler + processor) writes here; the Streamlit viewer
only ever reads from here. Neither side touches the filesystem directly
for anything other than its own well-defined job.

Design notes on incremental scanning
-------------------------------------
A project's identity is its path *relative to the scan root*
(``project_key``), never an absolute path or a bare folder name:

- An absolute path breaks the moment the root is mounted under a
  different drive letter or moved to another server — every project
  would look "new" again on the next scan.
- A bare folder name breaks the moment two different projects happen to
  share a name.

The same principle applies one level down: an image's identity is its
path *relative to its project* (``rel_path``), enforced as
``UNIQUE(project_id, rel_path)``. This is deliberately more granular than
tracking "new projects" only — it also catches new renders dropped into
an *already indexed* project, and lets a scan that was interrupted
partway through resume cleanly, since each image is recorded as it is
processed rather than all-at-once at the end.

Nothing about "is this new?" ever depends on a scan timestamp or run id.
Those are stored for display purposes only.
"""

import sqlite3
from pathlib import Path
from typing import Optional


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Open a connection with WAL mode enabled and schema ensured.

    WAL mode lets the Streamlit viewer read the database while a scan is
    writing to it concurrently, instead of hitting "database is locked".
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist yet. Safe to call on every connect."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id              INTEGER PRIMARY KEY,
            project_key     TEXT NOT NULL UNIQUE,
            name            TEXT NOT NULL,
            first_seen_at   TEXT NOT NULL,
            scan_completed  INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS images (
            id          INTEGER PRIMARY KEY,
            project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            rel_path    TEXT NOT NULL,
            thumb_name  TEXT NOT NULL,
            width       INTEGER NOT NULL,
            height      INTEGER NOT NULL,
            format      TEXT NOT NULL,
            size_bytes  INTEGER NOT NULL,
            UNIQUE(project_id, rel_path)
        );

        -- Single-row table holding facts about the most recent scan that
        -- the UI wants to surface (e.g. loose images sitting in the root
        -- that were intentionally not indexed — see crawler.py).
        CREATE TABLE IF NOT EXISTS scan_meta (
            id                  INTEGER PRIMARY KEY CHECK (id = 1),
            last_scan_at        TEXT,
            loose_image_count   INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    conn.commit()


def get_or_create_project(
    conn: sqlite3.Connection, project_key: str, name: str, scanned_at: str
) -> int:
    """Return the id of the project identified by ``project_key``.

    Inserts it if it doesn't exist yet. This is the entry point that makes
    a project's identity stable across runs: the same ``project_key``
    always resolves to the same row, regardless of when the scan runs.
    """
    conn.execute(
        """
        INSERT INTO projects (project_key, name, first_seen_at, scan_completed)
        VALUES (?, ?, ?, 0)
        ON CONFLICT(project_key) DO NOTHING
        """,
        (project_key, name, scanned_at),
    )
    row = conn.execute(
        "SELECT id FROM projects WHERE project_key = ?", (project_key,)
    ).fetchone()
    return row["id"]


def mark_project_scanned(conn: sqlite3.Connection, project_id: int) -> None:
    """Flag a project as fully processed for this scan run.

    Only set once every image under the project has been handled, so a
    scan that dies partway through leaves the project at 0 and gets
    revisited (not skipped) on the next run.
    """
    conn.execute(
        "UPDATE projects SET scan_completed = 1 WHERE id = ?", (project_id,)
    )


def get_indexed_rel_paths(conn: sqlite3.Connection, project_id: int) -> set[str]:
    """Return the set of image paths already indexed for a project.

    Fetched once per project (not queried per-image) so the incremental
    check is a single query instead of one round-trip per file.
    """
    rows = conn.execute(
        "SELECT rel_path FROM images WHERE project_id = ?", (project_id,)
    ).fetchall()
    return {row["rel_path"] for row in rows}


def insert_image(
    conn: sqlite3.Connection,
    project_id: int,
    rel_path: str,
    thumb_name: str,
    width: int,
    height: int,
    image_format: str,
    size_bytes: int,
) -> None:
    """Record a newly processed image. Ignored silently if already present."""
    conn.execute(
        """
        INSERT INTO images
            (project_id, rel_path, thumb_name, width, height, format, size_bytes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id, rel_path) DO NOTHING
        """,
        (project_id, rel_path, thumb_name, width, height, image_format, size_bytes),
    )


def update_scan_meta(
    conn: sqlite3.Connection, scanned_at: str, loose_image_count: int
) -> None:
    """Persist facts about the latest scan run for the UI to display."""
    conn.execute(
        """
        INSERT INTO scan_meta (id, last_scan_at, loose_image_count)
        VALUES (1, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            last_scan_at = excluded.last_scan_at,
            loose_image_count = excluded.loose_image_count
        """,
        (scanned_at, loose_image_count),
    )


def get_scan_meta(conn: sqlite3.Connection) -> Optional[sqlite3.Row]:
    """Return the latest scan's metadata, or None if no scan has run yet."""
    return conn.execute("SELECT * FROM scan_meta WHERE id = 1").fetchone()


# --- Read queries used by the Streamlit viewer -----------------------------


def list_projects(conn: sqlite3.Connection, search: str = "") -> list[sqlite3.Row]:
    """Return all projects with their image count, optionally name-filtered.

    ``search`` is matched case-insensitively as a substring of the project
    name so the viewer's search box can filter as the user types.
    """
    return conn.execute(
        """
        SELECT
            p.id,
            p.project_key,
            p.name,
            COUNT(i.id) AS image_count
        FROM projects p
        LEFT JOIN images i ON i.project_id = p.id
        WHERE p.name LIKE '%' || ? || '%' COLLATE NOCASE
        GROUP BY p.id
        ORDER BY p.name COLLATE NOCASE
        """,
        (search,),
    ).fetchall()


def get_project_by_key(conn: sqlite3.Connection, project_key: str) -> Optional[sqlite3.Row]:
    """Look up a single project by its stable key."""
    return conn.execute(
        "SELECT * FROM projects WHERE project_key = ?", (project_key,)
    ).fetchone()


def count_images(conn: sqlite3.Connection, project_id: int) -> int:
    """Total number of images in a project, used to drive pagination."""
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM images WHERE project_id = ?", (project_id,)
    ).fetchone()
    return row["n"]


def list_images(
    conn: sqlite3.Connection, project_id: int, offset: int = 0, limit: int = 60
) -> list[sqlite3.Row]:
    """Return a page of images for a project, ordered for stable pagination."""
    return conn.execute(
        """
        SELECT * FROM images
        WHERE project_id = ?
        ORDER BY rel_path
        LIMIT ? OFFSET ?
        """,
        (project_id, limit, offset),
    ).fetchall()


def get_image(conn: sqlite3.Connection, image_id: int) -> Optional[sqlite3.Row]:
    """Fetch a single image row for the detail view."""
    return conn.execute(
        "SELECT * FROM images WHERE id = ?", (image_id,)
    ).fetchone()
