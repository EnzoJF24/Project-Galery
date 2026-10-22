"""Build a realistic demo file server for trying out Project Gallery.

Usage:
    python scripts/make_demo_data.py            # creates ./demo_server
    python scripts/make_demo_data.py --out D:\\demo
    python scan.py --root demo_server
    streamlit run app.py

Downloads public-domain (CC0) architecture photos listed in
scripts/demo_manifest.json and lays them out as an architecture firm's
project share would actually look: every project organizes its renders
differently ("03_Renders/Final", "Visualization/Interior/Lobby",
"RENDERS/old"...), nests them at different depths and names files in its
own style. That inconsistency is exactly what the scanner is built to cope
with, so the demo exercises it on purpose.

The layout is deterministic: running the script twice produces the same
tree, and files that already exist are not downloaded again.
"""

import argparse
import io
import json
import random
import sys
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

MANIFEST_PATH = Path(__file__).with_name("demo_manifest.json")

# Some image hosts refuse requests that don't look like a browser coming
# from their own site.
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) project-gallery-demo"}
_REFERERS = {"stocksnap": "https://stocksnap.io/", "rawpixel": "https://www.rawpixel.com/"}

# (project name, photo categories it draws from, render count, folder layout)
# Folder layouts are intentionally inconsistent from project to project.
# Categories are listed in the same order as the folders they belong in;
# repeating a category gives it a bigger share of the project.
PROJECTS = [
    ("Alder Street Residence", ["exterior", "living", "kitchen"], 14,
     ["03_Renders/Final", "03_Renders/WIP/v2", "Client Review 2024-05"]),
    ("Harbor View Offices", ["commercial", "office", "office"], 12,
     ["Visualization/Exterior", "Visualization/Interior/Lobby", "Visualization/Interior/Level 12"]),
    ("Casa Mirador", ["exterior", "living", "bedroom"], 10,
     ["RENDERS", "RENDERS/old"]),
    ("Juniper Lofts", ["living", "kitchen", "bedroom", "bathroom"], 16,
     ["Marketing/Brochure Images", "Design/CGI/Units/Type A", "Design/CGI/Units/Type B"]),
    ("Lakeside Cabin", ["exterior", "living"], 7,
     ["images"]),
    ("Meridian Tower", ["commercial", "commercial", "office", "office"], 15,
     ["05 - Visuals/Exterior/Day", "05 - Visuals/Exterior/Night", "05 - Visuals/Interior/Amenities",
      "05 - Visuals/Interior/Typical Floor"]),
    ("Oakridge Family Home", ["exterior", "kitchen", "living", "bathroom"], 11,
     ["Renderings", "Renderings/Revisions/R3"]),
    ("Pinecrest Clinic", ["office", "commercial"], 8,
     ["_Deliverables/2024/Q3/Renders"]),
    ("Riverside Townhouses", ["exterior", "living", "kitchen"], 13,
     ["Phase 1/Renders", "Phase 2/Renders/Draft", "Phase 2/Renders/Approved"]),
    ("Saltwater Beach House", ["exterior", "living", "bedroom"], 9,
     ["Final Renders", "Final Renders/Hi-Res"]),
    ("The Foundry Coworking", ["commercial", "office", "office", "living"], 12,
     ["CGI/Street Front", "CGI/Ground Floor", "CGI/Mezzanine", "CGI/Members Lounge"]),
    ("Villa Serena", ["exterior", "living", "bathroom", "bedroom"], 14,
     ["Presentation", "Presentation/Extra Views", "Working/Renders/Test"]),
    ("Westbrook Kitchen Remodel", ["kitchen"], 6,
     ["Option A", "Option B", "Option C"]),
    ("Willow Creek Lodge", ["exterior", "living", "bedroom"], 10,
     ["Docs/Renders", "Docs/Renders/Interiors/Suites"]),
    ("Copper Ridge Hotel", ["commercial", "living", "bedroom", "bathroom"], 14,
     ["04_CGI/Exterior", "04_CGI/Lobby & Lounge", "04_CGI/Guest Rooms/King", "04_CGI/Guest Rooms/Suite"]),
    ("Elm Court Apartments", ["living", "kitchen", "bathroom"], 12,
     ["renders", "renders/unit 3B", "renders/unit 5A/alt"]),
    ("Northgate Medical Center", ["commercial", "office"], 10,
     ["Design Development/Visuals", "Design Development/Visuals/Waiting Areas"]),
    ("Summit Retail Plaza", ["commercial"], 8,
     ["Marketing/Leasing Brochure/Hero Images", "Marketing/Social"]),
]

# Each project names its files in its own style, the way different teams do.
_NAMING_STYLES = [
    lambda label, n, rng: f"{label.replace(' ', '_')}_v{rng.randint(1, 4)}.jpg",
    lambda label, n, rng: f"{n:02d}_{label.replace(' ', '')}.jpg",
    lambda label, n, rng: f"Render {n:02d} - {label}.jpg",
    lambda label, n, rng: f"{label.lower().replace(' ', '-')}-final.jpg",
    lambda label, n, rng: f"IMG_{4100 + n * 7}.jpg",
    lambda label, n, rng: f"{label.upper().replace(' ', '_')}_{n:03d}.jpg",
]

_LABELS = {
    "exterior": ["Front Elevation", "Street View", "Aerial", "Garden View", "Entrance", "Rear Facade", "Dusk View"],
    "commercial": ["Facade", "Plaza", "Main Entrance", "Night View", "Podium"],
    "office": ["Open Office", "Reception", "Meeting Room", "Lobby", "Breakout Area"],
    "living": ["Living Room", "Lounge", "Great Room", "Family Room"],
    "kitchen": ["Kitchen", "Kitchen Island", "Dining", "Pantry"],
    "bedroom": ["Master Bedroom", "Guest Bedroom", "Bedroom"],
    "bathroom": ["Bathroom", "Ensuite", "Powder Room"],
}


def load_manifest() -> dict[str, list[dict]]:
    """Group the manifest's photos by category."""
    photos = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    by_category: dict[str, list[dict]] = defaultdict(list)
    for photo in photos:
        by_category[photo["category"]].append(photo)
    return by_category


def plan_layout(by_category: dict[str, list[dict]]) -> list[tuple[Path, dict]]:
    """Decide which photo lands at which path. Pure and deterministic.

    Photos are dealt out so the same one is never reused until every photo
    in that category has been used once.
    """
    rng = random.Random(2024)
    decks = {cat: rng.sample(items, len(items)) for cat, items in by_category.items()}
    cursors = defaultdict(int)

    def draw(category: str) -> dict:
        deck = decks[category]
        photo = deck[cursors[category] % len(deck)]
        cursors[category] += 1
        return photo

    plan = []
    for project_index, (name, categories, count, folders) in enumerate(PROJECTS):
        naming = _NAMING_STYLES[project_index % len(_NAMING_STYLES)]
        used_names: set[str] = set()
        for n in range(1, count + 1):
            # Categories and folders are both split into contiguous blocks,
            # so related renders end up together (exteriors in the
            # "Exterior" folder, and so on), like a real team would file them.
            category = categories[(n - 1) * len(categories) // count]
            folder = folders[(n - 1) * len(folders) // count]
            label = rng.choice(_LABELS[category])
            base = naming(label, n, rng).removesuffix(".jpg")
            filename, copy = f"{base}.jpg", 2
            while f"{folder}/{filename}" in used_names:
                filename, copy = f"{base}-{copy}.jpg", copy + 1
            used_names.add(f"{folder}/{filename}")
            plan.append((Path(name) / folder / filename, draw(category)))
    return plan


def download(url: str, source: str, attempts: int = 3) -> bytes:
    headers = dict(_HEADERS)
    if source in _REFERERS:
        headers["Referer"] = _REFERERS[source]
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
                return response.read()
        except OSError:
            if attempt == attempts:
                raise
            time.sleep(2 * attempt)
    raise AssertionError("unreachable")


def build(out_dir: Path, cache_dir: Path) -> None:
    plan = plan_layout(load_manifest())

    # Download each distinct photo once, even when it appears in several
    # projects, then copy it into place.
    unique = {photo["url"]: photo for _, photo in plan}
    # The cache lives outside out_dir: every folder in out_dir is a project
    # to the scanner, so a cache folder in there would show up as one.
    cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch(photo: dict) -> tuple[str, Path | None]:
        cached = cache_dir / f"{photo['id']}.jpg"
        if not cached.exists():
            try:
                data = download(photo["url"], photo["source"])
                # Some hosts serve WebP regardless of the URL's extension;
                # re-encode so every demo ".jpg" really is a JPEG.
                with Image.open(io.BytesIO(data)) as img:
                    img.convert("RGB").save(cached, "JPEG", quality=92)
            except OSError as error:
                print(f"  ! could not download {photo['url']}: {error}", file=sys.stderr)
                return photo["url"], None
        return photo["url"], cached

    print(f"Downloading {len(unique)} public-domain photos...")
    with ThreadPoolExecutor(max_workers=8) as pool:
        cached_paths = dict(pool.map(fetch, unique.values()))

    written = 0
    for rel_path, photo in plan:
        source = cached_paths.get(photo["url"])
        if source is None:
            continue
        target = out_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(source.read_bytes())
        written += 1

    projects = len({rel_path.parts[0] for rel_path, _ in plan})
    print(f"Demo server ready at {out_dir.resolve()}")
    print(f"  {projects} projects, {written} renders")
    print(f"Next: python scan.py --root \"{out_dir}\"")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=Path("demo_server"),
                        help="Where to create the demo project folders (default: demo_server/).")
    parser.add_argument("--cache", type=Path, default=Path(".demo_cache"),
                        help="Where downloaded photos are cached between runs (default: .demo_cache/).")
    args = parser.parse_args()
    build(args.out, args.cache)


if __name__ == "__main__":
    main()
