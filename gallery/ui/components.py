"""Reusable HTML snippets for the gallery UI.

Project and file names come from folder names on the scanned file server —
effectively untrusted input. Everything interpolated into HTML here goes
through html.escape() first, since the app renders with
unsafe_allow_html=True to get real CSS hover effects on cards.
"""

import base64
from html import escape
from pathlib import Path


def image_to_data_uri(path: Path) -> str:
    """Encode an image file as a base64 data URI.

    Streamlit's injected HTML runs in a sandboxed context that can't load
    local file paths in <img src="...">, so thumbnails must be embedded
    directly as data URIs. Callers should wrap this in st.cache_data,
    since re-reading and re-encoding on every rerun would be wasteful.
    """
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def project_card_html(name: str, image_count: int, cover_thumb_src: str) -> str:
    """A clickable-looking card summarizing one project."""
    safe_name = escape(name)
    label = "image" if image_count == 1 else "images"
    return f"""
    <div class="gallery-card">
        <img src="{cover_thumb_src}" alt="{safe_name} cover" />
        <div class="gallery-card-body">
            <p class="gallery-card-title">{safe_name}</p>
            <p class="gallery-card-meta">{image_count} {label}</p>
        </div>
    </div>
    """


def image_card_html(thumb_src: str, filename: str) -> str:
    """A thumbnail card for a single image inside a project's grid."""
    safe_filename = escape(filename)
    return f"""
    <div class="gallery-card">
        <img src="{thumb_src}" alt="{safe_filename}" />
        <div class="gallery-card-body">
            <p class="gallery-card-title">{safe_filename}</p>
        </div>
    </div>
    """


def empty_state_html(message: str) -> str:
    """Centered placeholder shown when there's nothing to display."""
    return f'<div class="gallery-empty-state">{escape(message)}</div>'


def notice_html(message: str) -> str:
    """A small inline banner, used for the loose-images-in-root hint."""
    return f'<div class="gallery-notice">{escape(message)}</div>'
