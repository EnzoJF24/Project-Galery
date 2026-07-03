"""CSS injected into the Streamlit app to move it away from the default look.

Streamlit's theming API (.streamlit/config.toml) covers colors and fonts,
but hiding its own chrome and adding hover micro-interactions on cards
requires injecting raw CSS — there is no supported Python API for either.
"""

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', system-ui, sans-serif;
}

/* Hide Streamlit's default chrome (hamburger menu, footer, header bar) so
   the app reads as a standalone product rather than "a Streamlit script". */
#MainMenu, footer, header {
    visibility: hidden;
}

.block-container {
    padding-top: 2rem;
    max-width: 1200px;
}

/* Project / image cards, rendered as plain HTML by gallery/ui/components.py
   so real CSS transitions (impossible on native Streamlit widgets) apply. */
.gallery-card {
    background: var(--secondary-background-color, #F0EFEA);
    border-radius: 12px;
    overflow: hidden;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    margin-bottom: 1.25rem;
}

.gallery-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
}

.gallery-card img {
    width: 100%;
    aspect-ratio: 4 / 3;
    object-fit: cover;
    display: block;
}

.gallery-card-body {
    padding: 0.75rem 1rem;
}

.gallery-card-title {
    font-weight: 600;
    font-size: 0.95rem;
    margin: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.gallery-card-meta {
    font-size: 0.8rem;
    color: #6B6B65;
    margin: 0.15rem 0 0 0;
}

.gallery-empty-state {
    text-align: center;
    padding: 4rem 1rem;
    color: #6B6B65;
}

.gallery-notice {
    background: #FFF7E6;
    border: 1px solid #F0DBA3;
    border-radius: 8px;
    padding: 0.6rem 1rem;
    font-size: 0.85rem;
    margin-bottom: 1rem;
}
</style>
"""
