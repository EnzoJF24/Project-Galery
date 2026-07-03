"""Command-line entry point for indexing a project directory.

Usage:
    python scan.py --root <path>

Walks the given root directory, finds render images inside each top-level
project folder, and indexes them into the local SQLite database. Re-running
this command is safe and incremental: only images that aren't already in
the index get processed, so scanning a server with thousands of existing
renders after adding a handful of new ones is fast.
"""

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

from gallery import index
from gallery.config import DEFAULT_DB_PATH, DEFAULT_THUMBNAILS_DIR
from gallery.crawler import crawl
from gallery.processor import process_image, thumbnail_filename

logger = logging.getLogger("scan")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan a directory of project folders and index their "
        "render images into a local SQLite database for the Streamlit viewer."
    )
    parser.add_argument(
        "--root",
        required=True,
        type=Path,
        help="Path to the directory containing your project folders. "
        "Each direct subfolder of this path is treated as one project.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to the SQLite database file (default: {DEFAULT_DB_PATH}).",
    )
    parser.add_argument(
        "--thumbnails",
        type=Path,
        default=DEFAULT_THUMBNAILS_DIR,
        help=f"Directory where generated thumbnails are stored "
        f"(default: {DEFAULT_THUMBNAILS_DIR}).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess every image, even ones already in the index. "
        "Useful after changing the thumbnail size, for example.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print a line for every image processed, not just the summary.",
    )
    return parser.parse_args()


def run_scan(
    root: Path, db_path: Path, thumbnails_dir: Path, force: bool = False, verbose: bool = False
) -> None:
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(message)s",
    )

    conn = index.get_connection(db_path)
    result = crawl(root)
    scanned_at = datetime.now(timezone.utc).isoformat()

    new_projects = 0
    new_images = 0
    skipped_images = 0
    failed_images = 0

    for project in result.projects:
        is_new_project = index.get_project_by_key(conn, project.project_key) is None
        if is_new_project:
            new_projects += 1

        project_id = index.get_or_create_project(
            conn, project.project_key, project.name, scanned_at
        )

        already_indexed = (
            set() if force else index.get_indexed_rel_paths(conn, project_id)
        )

        for image in project.images:
            if image.rel_path in already_indexed:
                skipped_images += 1
                continue

            thumb_name = thumbnail_filename(project.project_key, image.rel_path)
            thumb_path = thumbnails_dir / thumb_name
            processed = process_image(image.absolute_path, thumb_path)

            if processed is None:
                failed_images += 1
                continue

            index.insert_image(
                conn,
                project_id,
                image.rel_path,
                processed.thumb_name,
                processed.width,
                processed.height,
                processed.format,
                processed.size_bytes,
            )
            new_images += 1
            if verbose:
                logger.info("Indexed %s/%s", project.name, image.rel_path)

        # Only flip once every image under this project has been handled,
        # so a scan killed midway leaves the project unflagged and it gets
        # revisited (not skipped) next time.
        index.mark_project_scanned(conn, project_id)
        conn.commit()

    index.update_scan_meta(conn, scanned_at, result.loose_image_count, str(root.resolve()))
    conn.commit()
    conn.close()

    print(f"Scan complete: {root}")
    print(f"  Projects found:   {len(result.projects)} ({new_projects} new)")
    print(f"  Images indexed:   {new_images}")
    print(f"  Images skipped:   {skipped_images} (already indexed)")
    if failed_images:
        print(f"  Images failed:    {failed_images} (see warnings above)")
    if result.loose_image_count:
        print(
            f"  Loose images:     {result.loose_image_count} found directly in "
            f"the root folder, not indexed (move them into a project folder)"
        )


if __name__ == "__main__":
    args = parse_args()
    run_scan(args.root, args.db, args.thumbnails, force=args.force, verbose=args.verbose)
