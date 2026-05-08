#!/usr/bin/env python3
"""
split_for_rml.py
Pre-splits the exploded CSVs by type so the RML mapping can assign
OWL classes conditionally without needing FnO functions.
Also filters "Under Construction" from prose text columns.

Run after explode_csv.py and clean_activities.py.
Writes into exploded/split/
"""

import re
import logging
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

EXP  = Path(__file__).parent / "exploded"
OUT  = EXP / "split"
OUT.mkdir(exist_ok=True)

UC_RE = re.compile(
    r"under\s*construction|needs\s*work|🛠|stub|coming\s+soon|to\s+be\s+added|work\s+in\s+progress",
    re.IGNORECASE,
)


def is_uc(text) -> bool:
    if not text or (isinstance(text, float)):
        return True
    text = str(text).strip()
    return len(text) < 30 or bool(UC_RE.search(text))


def save(df: pd.DataFrame, name: str):
    path = OUT / name
    df.to_csv(path, index=False, encoding="utf-8-sig")
    log.info(f"  {name:<50} {len(df):>6} rows")


# ── 1. aesthetics.csv — filter Under Construction from text columns ───────────
log.info("Filtering Under Construction from aesthetics.csv…")
aes = pd.read_csv(EXP / "aesthetics.csv", encoding="utf-8-sig", low_memory=False)

# Drop wiki meta-pages (names like "Aesthetics Wiki:Wanted Pages" that contain a colon)
before = len(aes)
aes = aes[~aes["name"].str.contains(":", na=False)].copy()
dropped = before - len(aes)
if dropped:
    log.info(f"  Dropped {dropped} wiki meta-page row(s)")

for col in ["text_visuals", "text_fashion", "text_music",
            "text_lifestyle", "text_interior", "text_art", "definition"]:
    if col in aes.columns:
        aes[col] = aes[col].apply(lambda v: "" if is_uc(v) else str(v).strip())
save(aes, "aesthetics.csv")   # also write cleaned version here for the mapping to use


# ── 2. Locations → country / city ────────────────────────────────────────────
log.info("Splitting locations…")
loc = pd.read_csv(EXP / "aesthetic_locations.csv", encoding="utf-8-sig")
save(loc[loc["loc_type"] == "country"].copy(), "locations_country.csv")
save(loc[loc["loc_type"] == "city"].copy(),    "locations_city.csv")


# ── 3. Creators → person / group / unknown ────────────────────────────────────
log.info("Splitting creators…")
cre = pd.read_csv(EXP / "aesthetic_creators.csv", encoding="utf-8-sig")
save(cre[cre["agent_type"] == "person"].copy(),  "creators_person.csv")
save(cre[cre["agent_type"] == "group"].copy(),   "creators_group.csv")
save(cre[cre["agent_type"] == "unknown"].copy(), "creators_unknown.csv")
# All creators combined (for the link triple — always uses akg:agent/ namespace)
save(cre.copy(), "creators_all.csv")


# ── 4. Coined-by → person / group / unknown ───────────────────────────────────
log.info("Splitting coined_by…")
coin = pd.read_csv(EXP / "aesthetic_coined_by.csv", encoding="utf-8-sig")
save(coin[coin["agent_type"] == "person"].copy(),  "coined_person.csv")
save(coin[coin["agent_type"] == "group"].copy(),   "coined_group.csv")
save(coin[coin["agent_type"] == "unknown"].copy(), "coined_unknown.csv")
save(coin.copy(), "coined_all.csv")


# ── 5. Artworks → one file per type ───────────────────────────────────────────
log.info("Splitting artworks…")
art = pd.read_csv(EXP / "aesthetic_artworks.csv", encoding="utf-8-sig")

TYPE_MAP = {
    "Film":      "artworks_film.csv",
    "TVShow":    "artworks_tvshow.csv",
    "Book":      "artworks_book.csv",
    "VideoGame": "artworks_videogame.csv",
    "Anime":     "artworks_anime.csv",
    "Song":      "artworks_song.csv",
    "Album":     "artworks_album.csv",
}
known_types = set(TYPE_MAP.keys())
for art_type, filename in TYPE_MAP.items():
    save(art[art["artwork_type"] == art_type].copy(), filename)
save(art[~art["artwork_type"].isin(known_types)].copy(), "artworks_other.csv")


# ── 6. Relations → one file per relation type ─────────────────────────────────
log.info("Splitting relations…")
rel = pd.read_csv(EXP / "aesthetic_relations.csv", encoding="utf-8-sig")

REL_MAP = {
    "relatedTo":    "relations_relatedTo.csv",
    "overlapsWith": "relations_overlapsWith.csv",
    "hasSubgenre":  "relations_hasSubgenre.csv",
    "isSubgenreOf": "relations_isSubgenreOf.csv",
    "follows":      "relations_follows.csv",
    "precedes":     "relations_precedes.csv",
}
for rel_type, filename in REL_MAP.items():
    save(rel[rel["relation_type"] == rel_type].copy(), filename)


# ── 7. Copy remaining files unchanged into split/ ────────────────────────────
log.info("Copying unchanged files…")
COPY_AS_IS = [
    "aesthetic_altnames.csv",
    "aesthetic_decades.csv",
    "aesthetic_figures.csv",
    "aesthetic_platforms.csv",
    "aesthetic_brands.csv",
    "aesthetic_motifs.csv",
    "aesthetic_values.csv",
    "aesthetic_colors.csv",
    "aesthetic_food.csv",
    "aesthetic_activities.csv",
    "aesthetic_locations.csv",
]
for fname in COPY_AS_IS:
    src = EXP / fname
    if src.exists():
        df = pd.read_csv(src, encoding="utf-8-sig")
        save(df, fname)

log.info("\nDone. All split files in exploded/split/")
