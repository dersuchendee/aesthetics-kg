#!/usr/bin/env python3
"""
prep_extras.py
Prepares additional split CSVs needed for the RML mapping updates:
  1. Adds intro_text column to aesthetics.csv (from enriched 'text' column)
  2. Splits aesthetic_locations.csv by loc_type → 4 type-filtered files
  3. Extracts blogs, podcasts, youtube_channels into separate CSVs
"""

import re
import unicodedata
import pandas as pd
from pathlib import Path

BASE    = Path(__file__).parent
SPLIT   = BASE / "exploded/split"
ENRICHED = BASE / "aesthetics_dataset_enriched.csv"

print("Loading source data…")
enriched = pd.read_csv(ENRICHED, low_memory=False)
aesthetics = pd.read_csv(SPLIT / "aesthetics.csv")

# ---------------------------------------------------------------------------
# 1. Add intro_text to aesthetics.csv
# ---------------------------------------------------------------------------
print("\n1. Patching aesthetics.csv with intro_text…")

# Build name → intro_text lookup from enriched (use 'text' column)
intro_map = {}
for _, row in enriched.iterrows():
    name = str(row.get("name", "")).strip()
    txt  = row.get("text", None)
    if name and pd.notna(txt):
        intro_map[name] = str(txt).strip()

aesthetics["intro_text"] = aesthetics["name"].map(intro_map)
n_filled = aesthetics["intro_text"].notna().sum()
print(f"  intro_text filled: {n_filled} / {len(aesthetics)}")

aesthetics.to_csv(SPLIT / "aesthetics.csv", index=False)
print("  Saved aesthetics.csv")

# ---------------------------------------------------------------------------
# 2. Split aesthetic_locations.csv by loc_type
# ---------------------------------------------------------------------------
print("\n2. Splitting aesthetic_locations.csv by loc_type…")

locs = pd.read_csv(SPLIT / "aesthetic_locations.csv")
for loc_type in ("city", "country", "region", "digital"):
    subset = locs[locs["loc_type"] == loc_type][["name", "slug", "location_slug"]]
    out = SPLIT / f"aesthetic_locations_{loc_type}.csv"
    subset.to_csv(out, index=False)
    print(f"  {loc_type}: {len(subset)} rows → {out.name}")

# ---------------------------------------------------------------------------
# 3. Extract online resources (blogs, podcasts, youtube_channels)
# ---------------------------------------------------------------------------
print("\n3. Extracting online resource CSVs…")

# Merge slug from split aesthetics to enriched (join on name)
name_to_slug = dict(zip(aesthetics["name"], aesthetics["slug"]))

_SLUG_STRIP = re.compile(r"[^\w\s-]")
_SLUG_COLLAPSE = re.compile(r"[\s_]+")

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode()
    text = text.lower()
    text = _SLUG_STRIP.sub("", text)
    text = _SLUG_COLLAPSE.sub("-", text)
    return text.strip("-")

_SEP = re.compile(r"\n+")
_IS_URL = re.compile(r"^https?://", re.IGNORECASE)

def parse_line(item: str):
    """Return (resource_name, resource_url). URL-only lines use domain as display name."""
    from urllib.parse import urlparse
    if _IS_URL.match(item):
        parsed = urlparse(item)
        display = parsed.netloc.lstrip("www.") or item
        return display, item
    return item, ""

def extract_resources(col_names: list[str]) -> pd.DataFrame:
    """Extract one row per resource (with resource_slug and optional resource_url)."""
    rows = []
    for _, row in enriched.iterrows():
        name = str(row.get("name", "")).strip()
        slug = name_to_slug.get(name)
        if not slug:
            continue
        for col in col_names:
            cell = row.get(col, None)
            if pd.isna(cell) or not str(cell).strip():
                continue
            for item in _SEP.split(str(cell)):
                item = item.strip()
                if len(item) < 3 or item.lower() in ("nan", "none"):
                    continue
                resource_name, resource_url = parse_line(item)
                rows.append({
                    "slug": slug,
                    "resource_name": resource_name,
                    "resource_slug": slugify(resource_name),
                    "resource_url": resource_url,
                })
    df = pd.DataFrame(rows).drop_duplicates(subset=["slug", "resource_slug"])
    return df

blogs    = extract_resources(["stext__blogs", "stext__blogs_and_writings"])
podcasts = extract_resources(["stext__podcasts", "stext__podcasts_radio"])
youtube  = extract_resources(["stext__youtube_channels"])
tumblr   = extract_resources(["stext__tumblr_blogs"])

blogs.to_csv(SPLIT / "aesthetic_blogs.csv", index=False)
podcasts.to_csv(SPLIT / "aesthetic_podcasts.csv", index=False)
youtube.to_csv(SPLIT / "aesthetic_youtube_channels.csv", index=False)
tumblr.to_csv(SPLIT / "aesthetic_tumblr_blogs.csv", index=False)

print(f"  blogs:            {len(blogs)} rows")
print(f"  podcasts:         {len(podcasts)} rows")
print(f"  youtube_channels: {len(youtube)} rows")
print(f"  tumblr_blogs:     {len(tumblr)} rows")

print("\nDone.")
