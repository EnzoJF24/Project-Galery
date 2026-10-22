"""Reusable HTML snippets and formatting helpers for the gallery UI.

Project, folder and file names come from the scanned file server —
effectively untrusted input. Everything interpolated into HTML here goes
through html.escape() first, since the app renders with
unsafe_allow_html=True to get real CSS hover effects on cards.
"""

import base64
from datetime import datetime, timezone
from html import escape
from pathlib import Path

# Small 2x2 grid glyph used as the product mark in the top bar and login.
_LOGO_SVG = (
    '<svg width="16" height="16" viewBox="0 0 16 16" fill="#0B1A2E" aria-hidden="true">'
    '<rect x="1" y="1" width="6" height="6" rx="1.5"/>'
    '<rect x="9" y="1" width="6" height="6" rx="1.5" opacity=".55"/>'
    '<rect x="1" y="9" width="6" height="6" rx="1.5" opacity=".55"/>'
    '<rect x="9" y="9" width="6" height="6" rx="1.5"/></svg>'
)

_FOLDER_SVG = (
    '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#F5B82E" '
    'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>'
)


# --- Formatting helpers ------------------------------------------------------


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


def format_bytes(size_bytes: int) -> str:
    """Human-readable file size: 980 KB, 4.2 MB, 1.3 GB."""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit in ("B", "KB") else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def format_relative_time(iso_timestamp: str, now: datetime | None = None) -> str:
    """'just now', '5 min ago', '3 h ago', or a date for anything older."""
    then = datetime.fromisoformat(iso_timestamp)
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    seconds = ((now or datetime.now(timezone.utc)) - then).total_seconds()
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{int(seconds // 60)} min ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)} h ago"
    return then.strftime("%b %d, %Y").replace(" 0", " ")


def pluralize(count: int, word: str) -> str:
    return f"{count:,} {word}" + ("" if count == 1 else "s")


def folder_label(folder: str) -> str:
    """Display name for an image's folder; "" means the project folder itself."""
    return folder or "(project root)"


# --- Page chrome -------------------------------------------------------------


def topbar_html(last_scan_at: str | None, scan_root: str | None) -> str:
    """Product header: brand on the left, index freshness on the right."""
    meta = ""
    if last_scan_at:
        # Only the root folder's name is shown; the full path (which can be
        # long and reveal a user's home directory) stays in the tooltip.
        root_name = scan_root.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1] if scan_root else ""
        root = f'<code title="{escape(scan_root)}">{escape(root_name)}</code>' if scan_root else ""
        meta = (
            f'<div class="pg-topbar-meta"><span class="pg-live-dot"></span>'
            f"Indexed {escape(format_relative_time(last_scan_at))}{root}</div>"
        )
    return (
        f'<div class="pg-topbar"><div class="pg-brand">'
        f'<span class="pg-logo">{_LOGO_SVG}</span>Project Gallery</div>{meta}</div>'
    )


def page_header_html(eyebrow: str, title: str, subtitle: str = "") -> str:
    sub = f'<p class="pg-subtitle">{escape(subtitle)}</p>' if subtitle else ""
    return (
        f'<p class="pg-eyebrow">{escape(eyebrow)}</p>'
        f'<h1 class="pg-title">{escape(title)}</h1>{sub}'
    )


def stats_html(stats: list[tuple[str, str]]) -> str:
    """A row of headline numbers. Values may carry a unit after a space
    (e.g. "312 MB"); the unit is rendered smaller than the number."""
    tiles = []
    for value, label in stats:
        number, _, unit = value.partition(" ")
        unit_html = f"<small>{escape(unit)}</small>" if unit else ""
        tiles.append(
            f'<div class="pg-stat"><div class="pg-stat-value">{escape(number)}{unit_html}</div>'
            f'<div class="pg-stat-label">{escape(label)}</div></div>'
        )
    return f'<div class="pg-stats">{"".join(tiles)}</div>'


def section_label_html(text: str, emphasis: str = "") -> str:
    strong = f"<b>{escape(emphasis)}</b> " if emphasis else ""
    return f'<p class="pg-section-label">{strong}{escape(text)}</p>'


def footer_html() -> str:
    return (
        '<div class="pg-footer">Project Gallery · read-only index — '
        "original files on the server are never modified</div>"
    )


# --- Cards -------------------------------------------------------------------


def project_card_html(
    name: str, image_count: int, folder_count: int, total_bytes: int, thumb_srcs: list[str]
) -> str:
    """A project summary card: a three-render mosaic plus counts."""
    safe_name = escape(name)
    # Mosaic needs three renders; smaller projects get a single cover.
    shown = thumb_srcs[:3] if len(thumb_srcs) >= 3 else thumb_srcs[:1]
    media_class = "pg-media pg-mosaic" if len(shown) == 3 else "pg-media"
    imgs = "".join(f'<img src="{src}" alt="" loading="lazy" />' for src in shown)
    badge = f'<span class="pg-badge"><b>{image_count:,}</b> {"render" if image_count == 1 else "renders"}</span>'
    return f"""
    <div class="pg-card">
        <div class="{media_class}">{imgs}{badge}</div>
        <div class="pg-card-body">
            <p class="pg-card-title" title="{safe_name}">{safe_name}</p>
            <p class="pg-card-meta">
                <span>{pluralize(folder_count, "source folder")}</span>
                <span>{escape(format_bytes(total_bytes))}</span>
            </p>
        </div>
    </div>
    """


def image_card_html(thumb_src: str, filename: str, folder: str, width: int, height: int) -> str:
    """A thumbnail card for a single image inside a project's grid."""
    safe_filename = escape(filename)
    safe_folder = escape(folder_label(folder))
    return f"""
    <div class="pg-card">
        <div class="pg-media"><img src="{thumb_src}" alt="{safe_filename}" loading="lazy" /></div>
        <div class="pg-card-body">
            <p class="pg-card-title" title="{safe_filename}">{safe_filename}</p>
            <p class="pg-card-meta">
                <span class="pg-path" title="{safe_folder}">{safe_folder}</span>
                <span>{width}×{height}</span>
            </p>
        </div>
    </div>
    """


def image_details_html(
    project_name: str, filename: str, position: int, total: int, rows: list[tuple[str, str, bool]]
) -> str:
    """Side panel for the detail view. ``rows`` are (label, value, is_path)."""
    items = "".join(
        f'<div class="pg-meta-row"><dt>{escape(label)}</dt>'
        f'<dd class="{"pg-mono" if is_path else ""}">{escape(value)}</dd></div>'
        for label, value, is_path in rows
    )
    return f"""
    <div class="pg-panel">
        <p class="pg-eyebrow">{escape(project_name)}</p>
        <h2>{escape(filename)}</h2>
        <p class="pg-position">Render {position:,} of {total:,}</p>
        <dl style="margin:0">{items}</dl>
    </div>
    """


# --- States ------------------------------------------------------------------


def empty_state_html(title: str, message: str = "", command: str = "") -> str:
    """Centered placeholder shown when there's nothing to display."""
    body = f"<p>{escape(message)}</p>" if message else ""
    code = f"<code>{escape(command)}</code>" if command else ""
    return (
        f'<div class="pg-empty">{_FOLDER_SVG}'
        f'<p class="pg-empty-title">{escape(title)}</p>{body}{code}</div>'
    )


def notice_html(message: str) -> str:
    """A small inline banner, used for the loose-images-in-root hint."""
    return f'<div class="pg-notice">{escape(message)}</div>'


def login_header_html() -> str:
    return (
        f'<div class="pg-topbar"><div class="pg-brand">'
        f'<span class="pg-logo">{_LOGO_SVG}</span>Project Gallery</div></div>'
        + page_header_html("Private library", "Sign in", "Enter the shared password to browse the render library.")
    )
