#!/usr/bin/env python3
"""
explode_csv.py
Reads aesthetics_dataset_enriched.csv and writes a set of flat CSV files
suitable for direct pyRML mapping (one row = one triple subject or object).

Output files (all in exploded/ subfolder):
  aesthetics.csv             — one row per aesthetic (identity + description)
  aesthetic_altnames.csv     — (aesthetic, altname)
  aesthetic_decades.csv      — (aesthetic, label, start_year, end_year)
  aesthetic_locations.csv    — (aesthetic, location, loc_type)  [city|country|place]
  aesthetic_creators.csv     — (aesthetic, creator, agent_type) [person|group|unknown]
  aesthetic_coined_by.csv    — (aesthetic, coined_by, agent_type)
  aesthetic_figures.csv      — (aesthetic, figure)
  aesthetic_platforms.csv    — (aesthetic, platform, is_primary) [true|false]
  aesthetic_brands.csv       — (aesthetic, brand)
  aesthetic_motifs.csv       — (aesthetic, motif)
  aesthetic_values.csv       — (aesthetic, value)
  aesthetic_themes.csv       — (aesthetic, theme)
  aesthetic_colors.csv       — (aesthetic, color)
  aesthetic_music.csv        — (aesthetic, music_item)
  aesthetic_fashion.csv      — (aesthetic, fashion_item)
  aesthetic_artworks.csv     — (aesthetic, title, artwork_type, year)
  aesthetic_food.csv         — (aesthetic, food_item)
  aesthetic_activities.csv   — (aesthetic, activity)
  aesthetic_relations.csv    — (aesthetic, related, relation_type)
"""

import re
import unicodedata
import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

SRC  = Path(__file__).parent / "aesthetics_dataset_enriched.csv"
OUT  = Path(__file__).parent / "exploded"
OUT.mkdir(exist_ok=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

_SEP = re.compile(r"\s*[,;]\s*|\s+/\s+")


def slugify(s) -> str:
    if not s or isinstance(s, float):
        return ""
    s = str(s).strip()
    # Strip trailing parenthetical annotation before slugifying
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:120]


def clean_val(s: str) -> str:
    """Strip orphan trailing ) that has no matching opening (."""
    s = s.strip()
    while s.endswith(")") and s.count(")") > s.count("("):
        s = s[:-1].rstrip()
    return s


def split_vals(s) -> list[str]:
    if not s or (isinstance(s, float)):
        return []
    text = str(s).strip()
    if not text or text.lower() in ("nan", "none", ""):
        return []
    return [clean_val(v.strip()) for v in _SEP.split(text)
            if v.strip() and v.strip() not in ("-", "/")]


def coalesce(*cols) -> str:
    """Return first non-empty string value from the provided strings."""
    for v in cols:
        if v and isinstance(v, str) and v.strip() and v.strip().lower() not in ("nan", "none"):
            return v.strip()
    return ""


_DECADE_RE = re.compile(
    r"(?P<qual>early|mid(?:-?century)?|late)?\s*"
    r"(?P<dec>\d{2,4})(?:'?s)?",
    re.IGNORECASE,
)


def parse_decade(s) -> list[tuple]:
    """Return list of (label, start_year, end_year) tuples."""
    if not s or (isinstance(s, float)):
        return []
    results = []
    for chunk in re.split(r"[,;]", str(s)):
        chunk = chunk.strip()
        m = _DECADE_RE.search(chunk)
        if not m:
            continue
        dec = int(m.group("dec"))
        if dec < 100:
            dec = 1900 + dec if dec >= 10 else 2000 + dec
        if dec < 1000:
            continue
        qual = (m.group("qual") or "").lower()
        if "early" in qual:
            start, end = dec, dec + 3
        elif "mid" in qual:
            start, end = dec + 4, dec + 6
        elif "late" in qual:
            start, end = dec + 7, dec + 9
        else:
            start, end = dec, dec + 9
        results.append((chunk.strip(), start, end))
    return results


def parse_artworks(s: str) -> list[tuple]:
    """
    Parse enriched__artworks column.
    Format per entry: "Title [Type] (Year)" joined by "; "
    Returns list of (title, artwork_type, year).
    """
    if not s or (isinstance(s, float)) or str(s).strip().lower() in ("nan", "none", ""):
        return []
    results = []
    for entry in str(s).split(";"):
        entry = entry.strip()
        if not entry:
            continue
        year_m = re.search(r"\((\d{4})\)\s*$", entry)
        year = year_m.group(1) if year_m else ""
        if year_m:
            entry = entry[:year_m.start()].strip()
        type_m = re.search(r"\[([^\]]+)\]\s*$", entry)
        art_type = type_m.group(1) if type_m else "Artwork"
        if type_m:
            entry = entry[:type_m.start()].strip()
        title = entry.strip()
        if title and len(title) > 1:
            results.append((title, art_type, year))
    return results


def parse_agent_types(agent_type_str: str) -> dict[str, str]:
    """
    Parse enriched__agent_type column.
    Format: "Name:person; Name2:group"
    Returns dict {name: type}.
    """
    if not agent_type_str or (isinstance(agent_type_str, float)):
        return {}
    result = {}
    for pair in str(agent_type_str).split(";"):
        pair = pair.strip()
        if ":" in pair:
            name, _, typ = pair.rpartition(":")
            result[name.strip()] = typ.strip()
    return result


def split_food_or_activities(s: str) -> list[str]:
    """Split on newlines and commas, strip short/empty items."""
    if not s or (isinstance(s, float)):
        return []
    items = re.split(r"[\n,;]+", str(s))
    return [i.strip() for i in items if i.strip() and len(i.strip()) > 2]


def first_description(row) -> str:
    """Return the first substantive prose description from section texts."""
    for col in ["stext__overview", "stext__history", "stext__origin", "stext__visuals"]:
        v = row.get(col, "")
        if v and isinstance(v, str) and len(v.strip()) > 80:
            return v.strip()[:2000]
    text = row.get("text", "")
    if text and isinstance(text, str):
        for line in text.split("\n"):
            line = line.strip()
            if len(line) > 80 and not line[0].isdigit():
                return line[:2000]
    return ""


# ── Load ─────────────────────────────────────────────────────────────────────

log.info("Loading enriched dataset…")
df = pd.read_csv(SRC, encoding="utf-8-sig", low_memory=False)
log.info(f"  {len(df)} rows, {len(df.columns)} columns")


# ── 1. aesthetics.csv ─────────────────────────────────────────────────────────
log.info("Building aesthetics.csv…")
rows = []
for _, r in df.iterrows():
    def stext(col):
        v = r.get(col, "")
        return str(v).strip()[:2000] if v and not pd.isna(v) and str(v).strip().lower() not in ("nan","") else ""
    rows.append({
        "name":          r["name"],
        "url":           r.get("url", ""),
        "definition":    first_description(r),
        "text_visuals":  stext("stext__visuals"),
        "text_fashion":  stext("stext__fashion"),
        "text_music":    stext("stext__music"),
        "text_lifestyle":stext("stext__lifestyle"),
        "text_interior": stext("stext__interior"),
        "text_art":      stext("stext__art"),
    })
pd.DataFrame(rows).to_csv(OUT / "aesthetics.csv", index=False, encoding="utf-8-sig")


# ── 2. aesthetic_altnames.csv ─────────────────────────────────────────────────
log.info("Building aesthetic_altnames.csv…")
rows = []
for _, r in df.iterrows():
    seen = set()
    sources = [
        r.get("box__other_names", ""),
        r.get("box__also_known_as", ""),
        r.get("box__origins__other_names", ""),
    ]
    for v in sources:
        for alt in split_vals(v):
            if alt and alt not in seen and alt != r["name"]:
                seen.add(alt)
                rows.append({"name": r["name"], "altname": alt})
pd.DataFrame(rows).to_csv(OUT / "aesthetic_altnames.csv", index=False, encoding="utf-8-sig")


# ── 3. aesthetic_decades.csv ──────────────────────────────────────────────────
log.info("Building aesthetic_decades.csv…")
rows = []
for _, r in df.iterrows():
    raw = coalesce(
        r.get("box__decade_of_origin", ""),
        r.get("box__origins__decade_of_origin", ""),
        r.get("box__decade", ""),
    )
    for label, start, end in parse_decade(raw):
        rows.append({"name": r["name"], "label": label,
                     "start_year": start, "end_year": end})
pd.DataFrame(rows).to_csv(OUT / "aesthetic_decades.csv", index=False, encoding="utf-8-sig")


# ── 4. aesthetic_locations.csv ────────────────────────────────────────────────
log.info("Building aesthetic_locations.csv…")
COUNTRIES = {
    "united states", "usa", "us", "united kingdom", "uk", "england", "japan",
    "france", "germany", "italy", "spain", "south korea", "korea", "russia",
    "brazil", "australia", "canada", "china", "india", "mexico", "sweden",
    "norway", "denmark", "finland", "netherlands", "poland", "ukraine",
    "worldwide", "global", "international", "western", "europe", "asia",
}
rows = []
for _, r in df.iterrows():
    raw = coalesce(
        r.get("box__location_of_origin", ""),
        r.get("box__origins__location_of_origin", ""),
        r.get("box__country", ""),
        r.get("box__location", ""),
    )
    for loc in split_vals(raw):
        if not loc or len(loc) < 2:
            continue
        loc_type = "country" if loc.lower() in COUNTRIES else "city"
        rows.append({"name": r["name"], "location": loc, "loc_type": loc_type})
pd.DataFrame(rows).to_csv(OUT / "aesthetic_locations.csv", index=False, encoding="utf-8-sig")


# ── 5. aesthetic_creators.csv ─────────────────────────────────────────────────
log.info("Building aesthetic_creators.csv…")
rows = []
for _, r in df.iterrows():
    agent_types = parse_agent_types(r.get("enriched__agent_type", ""))
    raw = coalesce(
        r.get("enriched__creators_clean", ""),
        r.get("box__creator_s", ""),
        r.get("box__creator/s", ""),
        r.get("box__origins__creator/s", ""),
    )
    for creator in split_vals(raw):
        if not creator or len(creator) < 2:
            continue
        agent_type = agent_types.get(creator, "unknown")
        rows.append({"name": r["name"], "creator": creator, "agent_type": agent_type})
pd.DataFrame(rows).to_csv(OUT / "aesthetic_creators.csv", index=False, encoding="utf-8-sig")


# ── 6. aesthetic_coined_by.csv ────────────────────────────────────────────────
log.info("Building aesthetic_coined_by.csv…")
rows = []
for _, r in df.iterrows():
    agent_types = parse_agent_types(r.get("enriched__agent_type", ""))
    raw = coalesce(
        r.get("box__coined_by", ""),
        r.get("box__origins__coined_by", ""),
    )
    for coined in split_vals(raw):
        if not coined or len(coined) < 2:
            continue
        agent_type = agent_types.get(coined, "unknown")
        rows.append({"name": r["name"], "coined_by": coined, "agent_type": agent_type})
pd.DataFrame(rows).to_csv(OUT / "aesthetic_coined_by.csv", index=False, encoding="utf-8-sig")


# ── 7. aesthetic_figures.csv ──────────────────────────────────────────────────
log.info("Building aesthetic_figures.csv…")
rows = []
for _, r in df.iterrows():
    seen = set()
    sources = [
        r.get("box__iconic_figures", ""),
        r.get("box__iconicfigures", ""),
        r.get("box__key_figures", ""),
        r.get("box__media_culture__iconic_figures", ""),
    ]
    for v in sources:
        for fig in split_vals(v):
            if fig and fig not in seen and len(fig) > 1:
                seen.add(fig)
                rows.append({"name": r["name"], "figure": fig})
pd.DataFrame(rows).to_csv(OUT / "aesthetic_figures.csv", index=False, encoding="utf-8-sig")


# ── 8. aesthetic_platforms.csv ────────────────────────────────────────────────
log.info("Building aesthetic_platforms.csv…")
rows = []
for _, r in df.iterrows():
    primary_raw = coalesce(
        r.get("box__primary_platform", ""),
        r.get("box__media_culture__primary_platform", ""),
        r.get("box__primaryplatform", ""),
    )
    seen = set()
    for p in split_vals(primary_raw):
        if p and p not in seen:
            seen.add(p)
            rows.append({"name": r["name"], "platform": p, "is_primary": "true"})
pd.DataFrame(rows).to_csv(OUT / "aesthetic_platforms.csv", index=False, encoding="utf-8-sig")


# ── 9. aesthetic_brands.csv ───────────────────────────────────────────────────
log.info("Building aesthetic_brands.csv…")
rows = []
for _, r in df.iterrows():
    raw = coalesce(
        r.get("box__related_brands", ""),
        r.get("box__media_culture__related_brands", ""),
        r.get("box__relatedbrands", ""),
    )
    for b in split_vals(raw):
        if b and len(b) > 1:
            rows.append({"name": r["name"], "brand": b})
pd.DataFrame(rows).to_csv(OUT / "aesthetic_brands.csv", index=False, encoding="utf-8-sig")


# ── 10. aesthetic_motifs.csv ──────────────────────────────────────────────────
log.info("Building aesthetic_motifs.csv…")
rows = []
for _, r in df.iterrows():
    raw = coalesce(
        r.get("box__key_motifs", ""),
        r.get("box__visuals_themes__key_motifs", ""),
    )
    for m in split_vals(raw):
        if m and len(m) > 1:
            rows.append({"name": r["name"], "motif": m})
pd.DataFrame(rows).to_csv(OUT / "aesthetic_motifs.csv", index=False, encoding="utf-8-sig")


# ── 11. aesthetic_values.csv ──────────────────────────────────────────────────
log.info("Building aesthetic_values.csv…")
rows = []
for _, r in df.iterrows():
    raw = coalesce(
        r.get("box__key_values", ""),
        r.get("box__visuals_themes__key_values", ""),
    )
    for v in split_vals(raw):
        if v and len(v) > 1:
            rows.append({"name": r["name"], "value": v})
pd.DataFrame(rows).to_csv(OUT / "aesthetic_values.csv", index=False, encoding="utf-8-sig")


# themes infobox field is empty; themes are captured via motifs/values which cover the same ground


# ── 13. aesthetic_colors.csv ──────────────────────────────────────────────────
log.info("Building aesthetic_colors.csv…")
rows = []
for _, r in df.iterrows():
    raw = coalesce(
        r.get("enriched__colors", ""),
        r.get("box__key_colours", ""),
        r.get("box__visuals_themes__key_colours", ""),
        r.get("box__color_palette", ""),
        r.get("box__colors", ""),
    )
    for c in split_vals(raw):
        if c and len(c) > 1 and c.lower() != "colors":
            rows.append({"name": r["name"], "color": c.lower()})
pd.DataFrame(rows).to_csv(OUT / "aesthetic_colors.csv", index=False, encoding="utf-8-sig")


# music and fashion structured infobox fields are empty in the dataset;
# prose descriptions are stored in aesthetics.csv as text_music / text_fashion


# ── 16. aesthetic_artworks.csv ────────────────────────────────────────────────
log.info("Building aesthetic_artworks.csv…")
rows = []
for _, r in df.iterrows():
    for title, art_type, year in parse_artworks(r.get("enriched__artworks", "")):
        rows.append({"name": r["name"], "title": title,
                     "artwork_type": art_type, "year": year})
pd.DataFrame(rows).to_csv(OUT / "aesthetic_artworks.csv", index=False, encoding="utf-8-sig")


# ── 17. aesthetic_food.csv ────────────────────────────────────────────────────
log.info("Building aesthetic_food.csv…")
rows = []
for _, r in df.iterrows():
    raw = r.get("stext__food", "")
    for item in split_food_or_activities(raw):
        if len(item) > 2:
            rows.append({"name": r["name"], "food_item": item})
pd.DataFrame(rows).to_csv(OUT / "aesthetic_food.csv", index=False, encoding="utf-8-sig")


# ── 18. aesthetic_activities.csv ──────────────────────────────────────────────
log.info("Building aesthetic_activities.csv…")
rows = []
for _, r in df.iterrows():
    raw = r.get("stext__activities", "")
    for item in split_food_or_activities(raw):
        if len(item) > 2:
            rows.append({"name": r["name"], "activity": item})
pd.DataFrame(rows).to_csv(OUT / "aesthetic_activities.csv", index=False, encoding="utf-8-sig")


# ── 19. aesthetic_relations.csv ───────────────────────────────────────────────
log.info("Building aesthetic_relations.csv…")

RELATION_SOURCES = [
    ("box__connections__related_aesthetics", "relatedTo"),
    ("box__related_aesthetics",              "relatedTo"),
    ("box__relatedaesthetics",               "relatedTo"),
    ("box__similar_aesthetics",              "relatedTo"),
    ("box__connections",                     "relatedTo"),
    ("box__connections__overlaps_with",      "overlapsWith"),
    ("box__overlaps_with",                   "overlapsWith"),
    ("box__overlapswith",                    "overlapsWith"),
    ("box__connections__subgenres",          "hasSubgenre"),
    ("box__subgenres",                       "hasSubgenre"),
    ("box__subsets",                         "hasSubgenre"),
    ("box__supersets",                       "isSubgenreOf"),
    ("box__preceded_by",                     "follows"),
    ("box__timeline__preceded_by",           "follows"),
    ("box__followed_by",                     "precedes"),
    ("box__succeeded_by",                    "precedes"),
    ("box__timeline__succeeded_by",          "precedes"),
]

rows = []
for _, r in df.iterrows():
    seen = set()
    for col, rel_type in RELATION_SOURCES:
        raw = r.get(col, "")
        for related in split_vals(raw):
            if not related or len(related) < 2:
                continue
            key = (r["name"], related, rel_type)
            if key not in seen:
                seen.add(key)
                rows.append({"name": r["name"], "related": related,
                             "relation_type": rel_type})
pd.DataFrame(rows).to_csv(OUT / "aesthetic_relations.csv", index=False, encoding="utf-8-sig")


# ── Add slug columns to all output files ─────────────────────────────────────
log.info("Adding slug columns…")
for f in sorted(OUT.glob("*.csv")):
    try:
        t = pd.read_csv(f, encoding="utf-8-sig", low_memory=False)
    except Exception:
        continue
    if t.empty or "name" not in t.columns:
        continue
    if "slug" not in t.columns:
        t.insert(1, "slug", t["name"].apply(slugify))
    # Also slugify secondary key columns
    for col, slug_col in [
        ("altname",      "altname_slug"),
        ("location",     "location_slug"),
        ("creator",      "creator_slug"),
        ("coined_by",    "coined_by_slug"),
        ("figure",       "figure_slug"),
        ("platform",     "platform_slug"),
        ("brand",        "brand_slug"),
        ("motif",        "motif_slug"),
        ("value",        "value_slug"),
        ("color",        "color_slug"),
        ("music_item",   "music_slug"),
        ("fashion_item", "fashion_slug"),
        ("title",        "artwork_slug"),
        ("food_item",    "food_slug"),
        ("activity",     "activity_slug"),
        ("related",      "related_slug"),
    ]:
        if col in t.columns and slug_col not in t.columns:
            t[slug_col] = t[col].apply(lambda x: slugify(str(x)) if pd.notna(x) else "")
    t.to_csv(f, index=False, encoding="utf-8-sig")

# ── Summary ───────────────────────────────────────────────────────────────────
log.info("\nDone. Files written to exploded/:")
for f in sorted(OUT.glob("*.csv")):
    try:
        t = pd.read_csv(f, encoding="utf-8-sig", low_memory=False)
        log.info(f"  {f.name:<35} {len(t):>6} rows, {len(t.columns)} cols")
    except Exception:
        pass
