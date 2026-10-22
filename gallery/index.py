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

    check_same_thread=False is required because Streamlit can execute a
    cached resource (like this connection) from a different thread than
    the one that created it across reruns. This app only ever accesses
    the connection sequentially within a single script run, so relaxing
    that check is safe here.
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
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
        -- that were intentionally not indexed — see crawler.py). scan_root
        -- is stored here purely so the viewer can locate original files for
        -- the full-resolution detail view; it is never used to decide
        -- what's "new" during a scan (see module docstring).
        CREATE TABLE IF NOT EXISTS scan_meta (
            id                  INTEGER PRIMARY KEY CHECK (id = 1),
            last_scan_at        TEXT,
            loose_image_count   INTEGER NOT NULL DEFAULT 0,
            scan_root           TEXT
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
    conn: sqlite3.Connection, scanned_at: str, loose_image_count: int, scan_root: str
) -> None:
    """Persist facts about the latest scan run for the UI to display."""
    conn.execute(
        """
        INSERT INTO scan_meta (id, last_scan_at, loose_image_count, scan_root)
        VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            last_scan_at = excluded.last_scan_at,
            loose_image_count = excluded.loose_image_count,
            scan_root = excluded.scan_root
        """,
        (scanned_at, loose_image_count, scan_root),
    )


def get_scan_meta(conn: sqlite3.Connection) -> Optional[sqlite3.Row]:
    """Return the latest scan's metadata, or None if no scan has run yet."""
    return conn.execute("SELECT * FROM scan_meta WHERE id = 1").fetchone()


# --- Read queries used by the Streamlit viewer -----------------------------


# Parent folder of an image, relative to its project ("" for files sitting
# directly in the project folder). SQLite has no dirname(): rtrim() with
# "every character except /" as the strip set cuts back to the last slash.
_FOLDER_SQL = "rtrim(rtrim(rel_path, replace(rel_path, '/', '')), '/')"

# How many folders deep an image sits below its project folder.
_DEPTH_SQL = "(length(rel_path) - length(replace(rel_path, '/', '')))"

_PROJECT_SORTS = {
    "name": "p.name COLLATE NOCASE",
    "images": "image_count DESC, p.name COLLATE NOCASE",
    "recent": "p.first_seen_at DESC, p.name COLLATE NOCASE",
}


def list_projects(
    conn: sqlite3.Connection, search: str = "", sort: str = "name"
) -> list[sqlite3.Row]:
    """Return all projects with their image count, optionally name-filtered.

    ``search`` is matched case-insensitively as a substring of the project
    name so the viewer's search box can filter as the user types. ``sort``
    is one of ``"name"``, ``"images"`` (largest first) or ``"recent"``
    (most recently discovered first).
    """
    order_by = _PROJECT_SORTS.get(sort, _PROJECT_SORTS["name"])
    return conn.execute(
        f"""
        SELECT
            p.id,
            p.project_key,
            p.name,
            p.first_seen_at,
            COUNT(i.id) AS image_count,
            COUNT(DISTINCT CASE WHEN i.id IS NOT NULL THEN {_FOLDER_SQL} END) AS folder_count,
            COALESCE(SUM(i.size_bytes), 0) AS total_bytes
        FROM projects p
        LEFT JOIN images i ON i.project_id = p.id
        WHERE p.name LIKE '%' || ? || '%' COLLATE NOCASE
        GROUP BY p.id
        ORDER BY {order_by}
        """,
        (search,),
    ).fetchall()


def get_library_stats(conn: sqlite3.Connection) -> sqlite3.Row:
    """Headline numbers for the whole index, shown at the top of the viewer."""
    return conn.execute(
        f"""
        SELECT
            (SELECT COUNT(*) FROM projects) AS project_count,
            COUNT(*) AS image_count,
            COALESCE(SUM(size_bytes), 0) AS total_bytes,
            COUNT(DISTINCT project_id || '/' || {_FOLDER_SQL}) AS folder_count,
            COALESCE(MAX({_DEPTH_SQL}), 0) AS max_depth
        FROM images
        """
    ).fetchone()


def list_project_folders(conn: sqlite3.Connection, project_id: int) -> list[sqlite3.Row]:
    """Every distinct folder a project's images were found in, with counts.

    This is what the viewer uses to show *where* renders actually live
    inside a project, since that structure is different in every project.
    """
    return conn.execute(
        f"""
        SELECT {_FOLDER_SQL} AS folder, COUNT(*) AS image_count
        FROM images
        WHERE project_id = ?
        GROUP BY folder
        ORDER BY folder COLLATE NOCASE
        """,
        (project_id,),
    ).fetchall()


def get_project_by_key(conn: sqlite3.Connection, project_key: str) -> Optional[sqlite3.Row]:
    """Look up a single project by its stable key."""
    return conn.execute(
        "SELECT * FROM projects WHERE project_key = ?", (project_key,)
    ).fetchone()


def _folder_filter(folder: Optional[str]) -> tuple[str, tuple]:
    """SQL fragment restricting images to one folder, or nothing for None."""
    if folder is None:
        return "", ()
    return f" AND {_FOLDER_SQL} = ?", (folder,)


def count_images(
    conn: sqlite3.Connection, project_id: int, folder: Optional[str] = None
) -> int:
    """Total number of images in a project (or one of its folders).

    Used to drive pagination.
    """
    folder_sql, folder_params = _folder_filter(folder)
    row = conn.execute(
        f"SELECT COUNT(*) AS n FROM images WHERE project_id = ?{folder_sql}",
        (project_id, *folder_params),
    ).fetchone()
    return row["n"]


def list_images(
    conn: sqlite3.Connection,
    project_id: int,
    offset: int = 0,
    limit: int = 60,
    folder: Optional[str] = None,
) -> list[sqlite3.Row]:
    """Return a page of images for a project, ordered for stable pagination.

    ``folder`` optionally restricts the page to images found directly in
    that folder (relative to the project, "" for the project folder itself).
    """
    folder_sql, folder_params = _folder_filter(folder)
    return conn.execute(
        f"""
        SELECT * FROM images
        WHERE project_id = ?{folder_sql}
        ORDER BY rel_path
        LIMIT ? OFFSET ?
        """,
        (project_id, *folder_params, limit, offset),
    ).fetchall()


def get_image_neighbors(
    conn: sqlite3.Connection, project_id: int, rel_path: str
) -> sqlite3.Row:
    """Previous/next image ids around ``rel_path`` plus its 1-based position.

    Follows the same ordering as list_images(), so stepping through the
    detail view matches the order of the project grid.
    """
    return conn.execute(
        """
        SELECT
            (SELECT id FROM images WHERE project_id = ? AND rel_path < ?
             ORDER BY rel_path DESC LIMIT 1) AS prev_id,
            (SELECT id FROM images WHERE project_id = ? AND rel_path > ?
             ORDER BY rel_path LIMIT 1) AS next_id,
            (SELECT COUNT(*) FROM images WHERE project_id = ? AND rel_path <= ?) AS position
        """,
        (project_id, rel_path, project_id, rel_path, project_id, rel_path),
    ).fetchone()


def get_image(conn: sqlite3.Connection, image_id: int) -> Optional[sqlite3.Row]:
    """Fetch a single image row for the detail view."""
    return conn.execute(
        "SELECT * FROM images WHERE id = ?", (image_id,)
    ).fetchone()


def get_image_with_project(conn: sqlite3.Connection, image_id: int) -> Optional[sqlite3.Row]:
    """Fetch an image joined with its project's key.

    Used by the detail view to reconstruct the original file's absolute
    path (scan_root + project_key + rel_path) so it can display the
    full-resolution image rather than the thumbnail.
    """
    return conn.execute(
        """
        SELECT images.*, projects.project_key, projects.name AS project_name
        FROM images
        JOIN projects ON projects.id = images.project_id
        WHERE images.id = ?
        """,
        (image_id,),
    ).fetchone()
