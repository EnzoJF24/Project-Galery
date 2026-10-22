"""CSS injected into the Streamlit app to move it away from the default look.

Streamlit's theming API (.streamlit/config.toml) covers colors and fonts,
but hiding its own chrome, turning whole cards into click targets and
adding hover micro-interactions requires injecting raw CSS — there is no
supported Python API for any of those.

Palette: deep navy surfaces with a single amber accent. Renders are the
content here, so the chrome stays dark and quiet to let the images carry
the color.
"""

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --pg-bg: #0B1A2E;
    --pg-surface: #11243D;
    --pg-surface-2: #16304F;
    --pg-border: #21395A;
    --pg-text: #EAF0F7;
    --pg-muted: #8FA3BD;
    --pg-faint: #5E7593;
    --pg-amber: #F5B82E;
    --pg-amber-soft: rgba(245, 184, 46, 0.12);
    --pg-radius: 14px;
    --pg-heading: 'Space Grotesk', 'Inter', system-ui, sans-serif;
    --pg-body: 'Inter', system-ui, sans-serif;
    --pg-mono: 'JetBrains Mono', ui-monospace, monospace;
}

html, body, .stApp, [class*="css"], button, input, textarea {
    font-family: var(--pg-body);
}

.stApp {
    background:
        radial-gradient(1200px 500px at 85% -10%, rgba(245, 184, 46, 0.07), transparent 60%),
        var(--pg-bg);
}

/* Hide Streamlit's default chrome (hamburger menu, footer, header bar) so
   the app reads as a standalone product rather than "a Streamlit script". */
#MainMenu, footer, header[data-testid="stHeader"] {
    visibility: hidden;
    height: 0;
}

.block-container {
    padding-top: 1.25rem;
    padding-bottom: 4rem;
    max-width: 1280px;
}

h1, h2, h3 {
    font-family: var(--pg-heading) !important;
    letter-spacing: -0.02em;
}

/* --- Top bar ------------------------------------------------------------ */

.pg-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.4rem 0 1.1rem 0;
    margin-bottom: 1.75rem;
    border-bottom: 1px solid var(--pg-border);
}

.pg-brand {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    font-family: var(--pg-heading);
    font-weight: 700;
    font-size: 1.1rem;
    color: var(--pg-text);
}

.pg-logo {
    width: 30px;
    height: 30px;
    border-radius: 8px;
    background: var(--pg-amber);
    display: grid;
    place-items: center;
}

.pg-topbar-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8rem;
    color: var(--pg-muted);
    min-width: 0;
}

.pg-topbar-meta code {
    font-family: var(--pg-mono);
    font-size: 0.75rem;
    color: var(--pg-text);
    background: var(--pg-surface);
    border: 1px solid var(--pg-border);
    border-radius: 6px;
    padding: 0.15rem 0.45rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 260px;
}

.pg-live-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #3DD68C;
    box-shadow: 0 0 0 3px rgba(61, 214, 140, 0.18);
    flex-shrink: 0;
}

/* --- Page header ---------------------------------------------------------- */

.pg-eyebrow {
    font-family: var(--pg-heading);
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--pg-amber);
    margin: 0 0 0.4rem 0;
}

.pg-title {
    font-family: var(--pg-heading);
    font-size: clamp(1.9rem, 3.2vw, 2.6rem);
    font-weight: 700;
    letter-spacing: -0.03em;
    line-height: 1.1;
    color: var(--pg-text);
    margin: 0;
}

.pg-subtitle {
    color: var(--pg-muted);
    font-size: 0.98rem;
    max-width: 640px;
    margin: 0.6rem 0 0 0;
    line-height: 1.55;
}

/* --- Stat strip ----------------------------------------------------------- */

.pg-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.75rem;
    margin: 1.75rem 0 1.5rem 0;
}

.pg-stat {
    background: var(--pg-surface);
    border: 1px solid var(--pg-border);
    border-radius: var(--pg-radius);
    padding: 0.9rem 1.1rem;
}

.pg-stat-value {
    font-family: var(--pg-heading);
    font-size: 1.65rem;
    font-weight: 700;
    color: var(--pg-text);
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
}

.pg-stat-value small {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--pg-muted);
    margin-left: 0.15rem;
}

.pg-stat:first-child .pg-stat-value {
    color: var(--pg-amber);
}

.pg-stat-label {
    font-size: 0.78rem;
    color: var(--pg-muted);
    margin-top: 0.2rem;
}

.pg-section-label {
    font-size: 0.8rem;
    color: var(--pg-muted);
    margin: 0.25rem 0 0.75rem 0;
}

.pg-section-label b {
    color: var(--pg-text);
    font-weight: 600;
}

/* --- Inputs --------------------------------------------------------------- */

[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background: var(--pg-surface) !important;
    border-color: var(--pg-border) !important;
    min-height: 44px;
}

[data-testid="stTextInput"] input:focus {
    border-color: var(--pg-amber) !important;
}

/* Buttons: quiet outline by default, amber on hover. */
[data-testid="stBaseButton-secondary"] {
    background: var(--pg-surface);
    border: 1px solid var(--pg-border);
    color: var(--pg-text);
    border-radius: 10px;
}

[data-testid="stBaseButton-secondary"]:hover:not(:disabled) {
    border-color: var(--pg-amber);
    color: var(--pg-amber);
}

[data-testid="stBaseButton-tertiary"] {
    color: var(--pg-muted);
    padding-left: 0;
}

[data-testid="stBaseButton-tertiary"]:hover {
    color: var(--pg-amber);
}

/* Folder filter pills */
[data-testid="stButtonGroup"] button {
    font-family: var(--pg-mono);
    font-size: 0.78rem;
}

/* --- Cards ---------------------------------------------------------------- */

/* Each card lives in a keyed st.container. A real (invisible) Streamlit
   button is stretched over the whole card so the entire surface is the
   click target, while the visible card stays plain HTML that real CSS
   transitions can animate. */
[class*="st-key-pcard_"],
[class*="st-key-icard_"] {
    position: relative;
    gap: 0;
    margin-bottom: 1.1rem;
}

[class*="st-key-pcard_"] [data-testid="stElementContainer"]:has([data-testid="stButton"]),
[class*="st-key-icard_"] [data-testid="stElementContainer"]:has([data-testid="stButton"]) {
    position: absolute;
    inset: 0;
    z-index: 5;
}

[class*="st-key-pcard_"] [data-testid="stButton"],
[class*="st-key-icard_"] [data-testid="stButton"],
[class*="st-key-pcard_"] [data-testid="stButton"] button,
[class*="st-key-icard_"] [data-testid="stButton"] button {
    width: 100%;
    height: 100%;
    opacity: 0;
    cursor: pointer;
}

.pg-card {
    background: var(--pg-surface);
    border: 1px solid var(--pg-border);
    border-radius: var(--pg-radius);
    overflow: hidden;
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

[class*="st-key-pcard_"]:hover .pg-card,
[class*="st-key-icard_"]:hover .pg-card {
    transform: translateY(-4px);
    border-color: rgba(245, 184, 46, 0.55);
    box-shadow: 0 14px 32px rgba(0, 0, 0, 0.35);
}

[class*="st-key-pcard_"]:has(button:focus-visible) .pg-card,
[class*="st-key-icard_"]:has(button:focus-visible) .pg-card {
    outline: 2px solid var(--pg-amber);
    outline-offset: 2px;
}

.pg-media {
    position: relative;
    aspect-ratio: 4 / 3;
    background: var(--pg-surface-2);
    overflow: hidden;
}

.pg-media img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    transition: transform 0.35s ease;
}

[class*="st-key-pcard_"]:hover .pg-media img,
[class*="st-key-icard_"]:hover .pg-media img {
    transform: scale(1.04);
}

/* Three-up mosaic on project cards: one hero render, two side renders. */
.pg-mosaic {
    display: grid;
    grid-template-columns: 2fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 2px;
}

.pg-mosaic img:first-child {
    grid-row: span 2;
}

.pg-badge {
    position: absolute;
    left: 0.6rem;
    bottom: 0.6rem;
    background: rgba(11, 26, 46, 0.82);
    backdrop-filter: blur(6px);
    color: var(--pg-text);
    font-size: 0.72rem;
    font-weight: 600;
    border-radius: 999px;
    padding: 0.2rem 0.6rem;
}

.pg-badge b {
    color: var(--pg-amber);
}

.pg-card-body {
    padding: 0.8rem 1rem 0.9rem 1rem;
}

.pg-card-title {
    font-family: var(--pg-heading);
    font-weight: 600;
    font-size: 1rem;
    color: var(--pg-text);
    margin: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.pg-card-meta {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    font-size: 0.78rem;
    color: var(--pg-muted);
    margin: 0.3rem 0 0 0;
}

.pg-card-meta span {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.pg-card-meta .pg-path {
    font-family: var(--pg-mono);
    font-size: 0.72rem;
    color: var(--pg-faint);
}

/* --- Detail panel --------------------------------------------------------- */

[data-testid="stImage"] img {
    border-radius: var(--pg-radius);
    border: 1px solid var(--pg-border);
}

.pg-panel {
    background: var(--pg-surface);
    border: 1px solid var(--pg-border);
    border-radius: var(--pg-radius);
    padding: 1.25rem 1.3rem;
    margin-bottom: 0.9rem;
}

.pg-panel h2 {
    font-size: 1.3rem;
    margin: 0 0 0.2rem 0;
    padding: 0;
    color: var(--pg-text);
    word-break: break-word;
}

.pg-position {
    font-size: 0.8rem;
    color: var(--pg-muted);
    margin: 0 0 1rem 0;
}

.pg-meta-row {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.55rem 0;
    border-top: 1px solid var(--pg-border);
    font-size: 0.85rem;
}

.pg-meta-row dt {
    color: var(--pg-muted);
    flex-shrink: 0;
}

.pg-meta-row dd {
    margin: 0;
    color: var(--pg-text);
    font-weight: 500;
    text-align: right;
    word-break: break-all;
}

.pg-meta-row dd.pg-mono {
    font-family: var(--pg-mono);
    font-size: 0.75rem;
    font-weight: 400;
}

/* --- States --------------------------------------------------------------- */

.pg-empty {
    text-align: center;
    padding: 4.5rem 1rem;
    border: 1px dashed var(--pg-border);
    border-radius: var(--pg-radius);
    color: var(--pg-muted);
}

.pg-empty-title {
    font-family: var(--pg-heading);
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--pg-text);
    margin: 0.75rem 0 0.35rem 0;
}

.pg-empty code {
    font-family: var(--pg-mono);
    background: var(--pg-surface);
    border: 1px solid var(--pg-border);
    border-radius: 6px;
    padding: 0.2rem 0.5rem;
    color: var(--pg-amber);
}

.pg-notice {
    background: var(--pg-amber-soft);
    border: 1px solid rgba(245, 184, 46, 0.35);
    color: var(--pg-text);
    border-radius: 10px;
    padding: 0.65rem 1rem;
    font-size: 0.85rem;
    margin-bottom: 1rem;
}

.pg-footer {
    margin-top: 3rem;
    padding-top: 1.25rem;
    border-top: 1px solid var(--pg-border);
    font-size: 0.75rem;
    color: var(--pg-faint);
    text-align: center;
}

@media (max-width: 640px) {
    .pg-topbar-meta code { display: none; }
    .pg-stats { grid-template-columns: repeat(2, 1fr); }
}
</style>
"""
