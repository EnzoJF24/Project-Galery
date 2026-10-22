"""Streamlit entry point for the Project Gallery viewer.

Usage:
    streamlit run app.py

Reads exclusively from the SQLite index built by scan.py — this app never
scans the filesystem directly. Run a scan first if the gallery is empty.
"""

from pathlib import Path

import streamlit as st

from gallery import index
from gallery.config import DEFAULT_DB_PATH, DEFAULT_THUMBNAILS_DIR
from gallery.ui import components
from gallery.ui.auth import require_password
from gallery.ui.styles import APP_CSS

PAGE_SIZE = 24  # images per page inside a project view
GRID_COLUMNS = 4

SORT_OPTIONS = {
    "Name (A–Z)": "name",
    "Most renders": "images",
    "Recently added": "recent",
}

st.set_page_config(page_title="Project Gallery", page_icon="🗂️", layout="wide")
st.markdown(APP_CSS, unsafe_allow_html=True)


@st.cache_resource
def get_connection():
    return index.get_connection(DEFAULT_DB_PATH)


# st.cache_data pickles return values, and sqlite3.Row isn't picklable —
# every cached query converts to plain dicts at this caching boundary.
# index.py itself keeps returning Row objects for callers that don't cache
# (scan.py, tests).


@st.cache_data(ttl=10)
def cached_list_projects(search: str, sort: str):
    return [dict(row) for row in index.list_projects(get_connection(), search, sort)]


@st.cache_data(ttl=10)
def cached_scan_meta():
    meta = index.get_scan_meta(get_connection())
    return dict(meta) if meta is not None else None


@st.cache_data(ttl=10)
def cached_library_stats():
    return dict(index.get_library_stats(get_connection()))


@st.cache_data(ttl=10)
def cached_project_folders(project_id: int):
    return [dict(row) for row in index.list_project_folders(get_connection(), project_id)]


@st.cache_data(ttl=10)
def cached_list_images(project_id: int, offset: int, limit: int, folder: str | None = None):
    rows = index.list_images(get_connection(), project_id, offset, limit, folder)
    return [dict(row) for row in rows]


@st.cache_data(ttl=10)
def cached_count_images(project_id: int, folder: str | None = None):
    return index.count_images(get_connection(), project_id, folder)


@st.cache_data
def cached_thumb_data_uri(thumb_name: str):
    return components.image_to_data_uri(DEFAULT_THUMBNAILS_DIR / thumb_name)


def _html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def _go_to(view: str, **params) -> None:
    st.session_state["view"] = view
    st.session_state.update(params)
    st.rerun()


def _folder_of(rel_path: str) -> str:
    parent = Path(rel_path).parent.as_posix()
    return "" if parent == "." else parent


def render_topbar() -> None:
    meta = cached_scan_meta()
    if meta is None:
        _html(components.topbar_html(None, None))
    else:
        _html(components.topbar_html(meta["last_scan_at"], meta["scan_root"]))


def render_gallery_view() -> None:
    meta = cached_scan_meta()
    if meta is None:
        _html(components.page_header_html("Render library", "All projects"))
        _html(
            components.empty_state_html(
                "No scan has been run yet",
                "Point the scanner at the folder that holds your projects:",
                "python scan.py --root <path>",
            )
        )
        return

    stats = cached_library_stats()
    _html(
        components.page_header_html(
            "Render library",
            "All projects",
            "Every render found on the file server, grouped by project — "
            "no matter which subfolder it was saved in or how deep it's buried.",
        )
    )
    depth = stats["max_depth"]
    _html(
        components.stats_html(
            [
                (f"{stats['image_count']:,}", "renders indexed"),
                (f"{stats['project_count']:,}", "projects"),
                (f"{stats['folder_count']:,}", "source folders scanned"),
                (f"{depth} {'level' if depth == 1 else 'levels'}", "deepest render found"),
                (components.format_bytes(stats["total_bytes"]), "library size"),
            ]
        )
    )

    if meta["loose_image_count"]:
        _html(
            components.notice_html(
                f"{meta['loose_image_count']} image(s) were found directly in the "
                "scan root and are not shown here — images must live inside a "
                "project folder to be indexed."
            )
        )

    col_search, col_sort = st.columns([3, 1])
    search = col_search.text_input(
        "Search projects",
        placeholder="Search projects by name…",
        label_visibility="collapsed",
    )
    sort_label = col_sort.selectbox(
        "Sort projects", list(SORT_OPTIONS), label_visibility="collapsed"
    )
    projects = cached_list_projects(search, SORT_OPTIONS[sort_label])

    if not projects:
        if search:
            _html(components.empty_state_html("No matching projects", f'Nothing matches "{search}".'))
        else:
            _html(components.empty_state_html("No projects indexed yet"))
        return

    shown = components.pluralize(len(projects), "project")
    _html(components.section_label_html(f"matching “{search}”" if search else "", shown))

    columns = st.columns(GRID_COLUMNS)
    for position, project in enumerate(projects):
        with columns[position % GRID_COLUMNS]:
            covers = cached_list_images(project["id"], 0, 3)
            thumbs = [cached_thumb_data_uri(image["thumb_name"]) for image in covers]
            with st.container(key=f"pcard_{project['id']}"):
                _html(
                    components.project_card_html(
                        project["name"],
                        project["image_count"],
                        project["folder_count"],
                        project["total_bytes"],
                        thumbs,
                    )
                )
                if st.button(f"Open {project['name']}", key=f"open_{project['id']}"):
                    _go_to(
                        "project",
                        project_id=project["id"],
                        project_name=project["name"],
                        page=0,
                        folder=None,
                    )


def render_project_view() -> None:
    project_id = st.session_state["project_id"]
    project_name = st.session_state["project_name"]
    page = st.session_state.get("page", 0)
    folder = st.session_state.get("folder")

    if st.button("←  All projects", type="tertiary"):
        _go_to("gallery")

    folders = cached_project_folders(project_id)
    total_all = sum(row["image_count"] for row in folders)
    project = next(
        (p for p in cached_list_projects("", "name") if p["id"] == project_id), None
    )
    size = components.format_bytes(project["total_bytes"]) if project else ""
    _html(
        components.page_header_html(
            "Project",
            project_name,
            f"{components.pluralize(total_all, 'render')} found across "
            f"{components.pluralize(len(folders), 'folder')} · {size}",
        )
    )

    if total_all == 0:
        _html(components.empty_state_html("This project has no indexed images"))
        return

    # Folder filter: shows exactly where renders were found inside this
    # project, which is different for every project on a real server.
    st.write("")
    all_label = f"All folders · {total_all}"
    options = [all_label] + [
        f"{components.folder_label(row['folder'])} · {row['image_count']}" for row in folders
    ]
    option_folders = {all_label: None} | {
        label: row["folder"] for label, row in zip(options[1:], folders)
    }
    current_label = next(
        (label for label, value in option_folders.items() if value == folder), all_label
    )
    picked = st.pills(
        "Where the renders were found",
        options,
        default=current_label,
        key=f"folder_pills_{project_id}",
    )
    picked_folder = option_folders.get(picked) if picked else None
    if picked_folder != folder:
        _go_to("project", project_id=project_id, project_name=project_name, page=0, folder=picked_folder)

    total = cached_count_images(project_id, folder)
    offset = page * PAGE_SIZE
    images = cached_list_images(project_id, offset, PAGE_SIZE, folder)
    st.write("")

    columns = st.columns(GRID_COLUMNS)
    for position, image in enumerate(images):
        with columns[position % GRID_COLUMNS]:
            with st.container(key=f"icard_{image['id']}"):
                _html(
                    components.image_card_html(
                        cached_thumb_data_uri(image["thumb_name"]),
                        Path(image["rel_path"]).name,
                        _folder_of(image["rel_path"]),
                        image["width"],
                        image["height"],
                    )
                )
                if st.button(f"View {image['rel_path']}", key=f"view_{image['id']}"):
                    _go_to(
                        "image",
                        image_id=image["id"],
                        return_project_id=project_id,
                        return_project_name=project_name,
                        return_page=page,
                    )

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if total_pages > 1:
        col_prev, col_label, col_next = st.columns([1, 2, 1], vertical_alignment="center")
        if col_prev.button("← Previous", disabled=page <= 0, width="stretch"):
            _go_to("project", project_id=project_id, project_name=project_name, page=page - 1)
        col_label.markdown(
            f"<p class='pg-section-label' style='text-align:center;margin:0'>"
            f"Page <b>{page + 1}</b> of {total_pages} · {total:,} renders</p>",
            unsafe_allow_html=True,
        )
        if col_next.button("Next →", disabled=page >= total_pages - 1, width="stretch"):
            _go_to("project", project_id=project_id, project_name=project_name, page=page + 1)


def render_image_view() -> None:
    conn = get_connection()
    image = index.get_image_with_project(conn, st.session_state["image_id"])
    project_name = st.session_state["return_project_name"]

    if st.button(f"←  {project_name}", type="tertiary"):
        _go_to(
            "project",
            project_id=st.session_state["return_project_id"],
            project_name=project_name,
            page=st.session_state["return_page"],
        )

    if image is None:
        _html(components.empty_state_html("This image is no longer in the index"))
        return

    meta = cached_scan_meta()
    original_path = (
        Path(meta["scan_root"]) / image["project_key"] / image["rel_path"]
        if meta and meta["scan_root"]
        else None
    )
    neighbors = index.get_image_neighbors(conn, image["project_id"], image["rel_path"])
    total = cached_count_images(image["project_id"])

    col_image, col_info = st.columns([2.6, 1], gap="large")
    with col_image:
        if original_path and original_path.exists():
            st.image(str(original_path), width="stretch")
        else:
            st.image(str(DEFAULT_THUMBNAILS_DIR / image["thumb_name"]), width="stretch")
            st.caption("Original file not reachable — showing the thumbnail instead.")

    with col_info:
        width, height = image["width"], image["height"]
        _html(
            components.image_details_html(
                image["project_name"],
                Path(image["rel_path"]).name,
                neighbors["position"],
                total,
                [
                    ("Dimensions", f"{width} × {height} px", False),
                    ("Resolution", f"{width * height / 1_000_000:.1f} MP", False),
                    ("Format", image["format"], False),
                    ("File size", components.format_bytes(image["size_bytes"]), False),
                    ("Folder", components.folder_label(_folder_of(image["rel_path"])), True),
                    ("Full path", f"{image['project_key']}/{image['rel_path']}", True),
                ],
            )
        )
        col_prev, col_next = st.columns(2)
        for column, label, target in (
            (col_prev, "← Previous", neighbors["prev_id"]),
            (col_next, "Next →", neighbors["next_id"]),
        ):
            if column.button(label, disabled=target is None, width="stretch"):
                _go_to("image", image_id=target)


def main() -> None:
    if not require_password():
        return

    st.session_state.setdefault("view", "gallery")
    render_topbar()

    view = st.session_state["view"]
    if view == "project":
        render_project_view()
    elif view == "image":
        render_image_view()
    else:
        render_gallery_view()

    _html(components.footer_html())


if __name__ == "__main__":
    main()
