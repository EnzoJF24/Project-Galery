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

st.set_page_config(page_title="Project Gallery", layout="wide")
st.markdown(APP_CSS, unsafe_allow_html=True)


@st.cache_resource
def get_connection():
    return index.get_connection(DEFAULT_DB_PATH)


@st.cache_data(ttl=10)
def cached_list_projects(search: str):
    # st.cache_data pickles return values, and sqlite3.Row isn't picklable —
    # convert to plain dicts at this caching boundary. index.py itself keeps
    # returning Row objects for callers that don't cache (scan.py, tests).
    conn = get_connection()
    return [dict(row) for row in index.list_projects(conn, search)]


@st.cache_data(ttl=10)
def cached_scan_meta():
    conn = get_connection()
    meta = index.get_scan_meta(conn)
    return dict(meta) if meta is not None else None


@st.cache_data(ttl=10)
def cached_list_images(project_id: int, offset: int, limit: int):
    conn = get_connection()
    return [dict(row) for row in index.list_images(conn, project_id, offset, limit)]


@st.cache_data(ttl=10)
def cached_count_images(project_id: int):
    conn = get_connection()
    return index.count_images(conn, project_id)


@st.cache_data
def cached_thumb_data_uri(thumb_name: str):
    return components.image_to_data_uri(DEFAULT_THUMBNAILS_DIR / thumb_name)


def _go_to(view: str, **params) -> None:
    st.session_state["view"] = view
    st.session_state.update(params)
    st.rerun()


def render_gallery_view() -> None:
    st.title("Project Gallery")

    meta = cached_scan_meta()
    if meta is None:
        st.markdown(
            components.empty_state_html(
                "No scan has been run yet. Index a directory first: "
                "python scan.py --root <path>"
            ),
            unsafe_allow_html=True,
        )
        return

    if meta["loose_image_count"]:
        st.markdown(
            components.notice_html(
                f"{meta['loose_image_count']} image(s) were found directly in the "
                "scan root and are not shown here — images must live inside a "
                "project folder to be indexed."
            ),
            unsafe_allow_html=True,
        )

    search = st.text_input("Search projects", placeholder="Type a project name...")
    projects = cached_list_projects(search)

    if not projects:
        message = (
            "No projects match your search." if search else "No projects indexed yet."
        )
        st.markdown(components.empty_state_html(message), unsafe_allow_html=True)
        return

    columns = st.columns(4)
    for position, project in enumerate(projects):
        with columns[position % 4]:
            cover_images = cached_list_images(project["id"], 0, 1)
            cover_src = (
                cached_thumb_data_uri(cover_images[0]["thumb_name"])
                if cover_images
                else ""
            )
            st.markdown(
                components.project_card_html(
                    project["name"], project["image_count"], cover_src
                ),
                unsafe_allow_html=True,
            )
            if st.button("Open", key=f"open_{project['id']}", use_container_width=True):
                _go_to("project", project_id=project["id"], project_name=project["name"], page=0)


def render_project_view() -> None:
    project_id = st.session_state["project_id"]
    project_name = st.session_state["project_name"]
    page = st.session_state.get("page", 0)

    if st.button("< Back to all projects"):
        _go_to("gallery")

    st.title(project_name)

    total = cached_count_images(project_id)
    if total == 0:
        st.markdown(
            components.empty_state_html("This project has no indexed images."),
            unsafe_allow_html=True,
        )
        return

    offset = page * PAGE_SIZE
    images = cached_list_images(project_id, offset, PAGE_SIZE)

    columns = st.columns(4)
    for position, image in enumerate(images):
        with columns[position % 4]:
            thumb_src = cached_thumb_data_uri(image["thumb_name"])
            filename = Path(image["rel_path"]).name
            st.markdown(
                components.image_card_html(thumb_src, filename),
                unsafe_allow_html=True,
            )
            if st.button("View", key=f"view_{image['id']}", use_container_width=True):
                _go_to(
                    "image",
                    image_id=image["id"],
                    return_project_id=project_id,
                    return_project_name=project_name,
                    return_page=page,
                )

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    st.caption(f"Page {page + 1} of {total_pages} · {total} images")
    col_prev, col_next = st.columns(2)
    if col_prev.button("< Previous", disabled=page <= 0):
        _go_to("project", project_id=project_id, project_name=project_name, page=page - 1)
    if col_next.button("Next >", disabled=page >= total_pages - 1):
        _go_to("project", project_id=project_id, project_name=project_name, page=page + 1)


def render_image_view() -> None:
    conn = get_connection()
    image = index.get_image_with_project(conn, st.session_state["image_id"])

    if st.button(f"< Back to {st.session_state['return_project_name']}"):
        _go_to(
            "project",
            project_id=st.session_state["return_project_id"],
            project_name=st.session_state["return_project_name"],
            page=st.session_state["return_page"],
        )

    if image is None:
        st.markdown(
            components.empty_state_html("This image is no longer in the index."),
            unsafe_allow_html=True,
        )
        return

    st.subheader(Path(image["rel_path"]).name)

    meta = cached_scan_meta()
    original_path = (
        Path(meta["scan_root"]) / image["project_key"] / image["rel_path"]
        if meta and meta["scan_root"]
        else None
    )
    if original_path and original_path.exists():
        st.image(str(original_path))
    else:
        st.caption("Original file not reachable — showing thumbnail instead.")
        st.image(str(DEFAULT_THUMBNAILS_DIR / image["thumb_name"]))

    st.markdown(
        f"""
        - **Dimensions:** {image['width']} x {image['height']} px
        - **Format:** {image['format']}
        - **Size:** {image['size_bytes'] / 1024:.1f} KB
        - **Path:** `{image['rel_path']}`
        """
    )


def main() -> None:
    if not require_password():
        return

    st.session_state.setdefault("view", "gallery")

    view = st.session_state["view"]
    if view == "project":
        render_project_view()
    elif view == "image":
        render_image_view()
    else:
        render_gallery_view()


if __name__ == "__main__":
    main()
