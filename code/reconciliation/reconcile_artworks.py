#!/usr/bin/env python3
"""
reconcile_artworks.py
Links artwork titles (films, albums, books, anime, TV shows, video games)
to Wikidata QIDs via the Wikipedia Action API (pageprops → wikibase_item).
Batches 50 titles per request; results cached to artwork_cache.json.

Strategy:
  Pass 1 — plain title lookup → Wikidata QID (skipped for tvshow/videogame,
            too ambiguous without a type suffix).
  Pass 2 — type-qualified fallback ("Dune (novel)", "The Witcher (TV series)")
            for disambiguation pages or misses.

Run from aestheticswork/:
    python3 reconcile_artworks.py
Then re-run:
    python3 run_rml.py
"""

import json
import time
import logging
from pathlib import Path

import requests
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

BASE       = Path(__file__).parent
SPLIT      = BASE / "exploded" / "split"
CACHE_FILE = BASE / "artwork_cache.json"

WP_API = "https://en.wikipedia.org/w/api.php"
BATCH  = 50   # Wikipedia API hard limit per request

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "AestheticsKG/1.0 (wikidata reconciliation)"})

# Ordered fallback suffixes per type — tried in sequence until a hit is found
TYPE_SUFFIXES: dict[str, list[str]] = {
    "film":      ["(film)", "(movie)", "(film series)"],
    "album":     ["(album)", "(soundtrack)", "(EP)"],
    "book":      ["(novel)", "(book)", "(series)"],
    "anime":     ["(anime)", "(TV series)", "(manga)"],
    "tvshow":    ["(TV series)", "(television series)", "(animated series)", "(miniseries)", "(TV film)"],
    "videogame": ["(video game)", "(video game series)", "(game)"],
}

# For these types, plain-title pass-1 is too ambiguous (same name as film/book/etc.)
# — go straight to type-qualified suffixes only.
SKIP_PLAIN_LOOKUP: set[str] = {"tvshow", "videogame"}


# ── cache ─────────────────────────────────────────────────────────────────────

def load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict):
    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── Wikipedia Action API ──────────────────────────────────────────────────────

def wp_batch(titles: list[str]) -> dict[str, dict]:
    """
    Query Wikipedia for up to 50 titles in one request.
    Returns {queried_title: page_dict}, resolving redirects and normalisations
    back to the original queried form.
    """
    if not titles:
        return {}

    params = {
        "action":  "query",
        "titles":  "|".join(titles),
        "prop":    "pageprops",
        "ppprop":  "wikibase_item|disambiguation",
        "redirects": "1",
        "format":  "json",
    }
    for attempt in range(3):
        try:
            r = SESSION.get(WP_API, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            break
        except Exception as e:
            log.warning(f"  Wikipedia API error (attempt {attempt+1}): {e}")
            time.sleep(3 * (attempt + 1))
    else:
        return {}

    # Build resolved-title → page map
    normalised = {n["from"]: n["to"]
                  for n in data.get("query", {}).get("normalized", [])}
    redirects  = {rd["from"]: rd["to"]
                  for rd in data.get("query", {}).get("redirects", [])}
    pages_by_title = {p["title"]: p
                      for p in data.get("query", {}).get("pages", {}).values()}

    out: dict[str, dict] = {}
    for orig in titles:
        resolved = normalised.get(orig, orig)
        resolved = redirects.get(resolved, resolved)
        if resolved in pages_by_title:
            out[orig] = pages_by_title[resolved]
    return out


def is_disambiguation(page: dict) -> bool:
    return "disambiguation" in page.get("pageprops", {})


def qid_to_uri(page: dict) -> str:
    qid = page.get("pageprops", {}).get("wikibase_item", "")
    return f"https://www.wikidata.org/entity/{qid}" if qid else ""


# ── core reconciliation ───────────────────────────────────────────────────────

def reconcile_titles(
    titles: list[str], artwork_type: str, cache: dict
) -> dict[str, str]:  # noqa: C901
    """
    Returns {title: wikidata_uri} for every title in the list.
    Reads from cache first; makes network calls only for cache misses.
    """
    todo   = [t for t in titles if t and f"{artwork_type}:{t}" not in cache]
    result = {t: cache[f"{artwork_type}:{t}"]
              for t in titles if f"{artwork_type}:{t}" in cache}

    log.info(f"    {len(result)} cached, {len(todo)} to query")
    if not todo:
        return result

    fresh: dict[str, str] = {}
    needs_fallback: list[str] = []

    # Pass 1 — plain titles (skipped for types where plain title is too ambiguous)
    if artwork_type in SKIP_PLAIN_LOOKUP:
        needs_fallback = list(todo)
        log.info(f"    skipping plain-title pass for '{artwork_type}' (ambiguity risk)")

    for i in range(0, len(todo) if artwork_type not in SKIP_PLAIN_LOOKUP else 0, BATCH):
        chunk = todo[i : i + BATCH]
        pages = wp_batch(chunk)
        time.sleep(0.3)

        for title in chunk:
            page = pages.get(title)
            if not page or "missing" in page:
                needs_fallback.append(title)
                continue
            if is_disambiguation(page):
                needs_fallback.append(title)
                continue
            uri = qid_to_uri(page)
            cache[f"{artwork_type}:{title}"] = uri
            fresh[title] = uri

        matched = sum(1 for v in fresh.values() if v)
        log.info(
            f"    pass-1 batch {i//BATCH+1}/{-(-len(todo)//BATCH)} — "
            f"{matched}/{len(fresh)} matched  ({len(needs_fallback)} need fallback)"
        )
        save_cache(cache)

    # Pass 2 — type-qualified fallbacks for disambiguation/missing
    suffixes = TYPE_SUFFIXES.get(artwork_type, [])
    for suffix in suffixes:
        remaining = [t for t in needs_fallback if f"{artwork_type}:{t}" not in cache]
        if not remaining:
            break
        log.info(f"    fallback '{suffix}': {len(remaining)} titles")

        qualified_to_orig = {f"{t} {suffix}": t for t in remaining}

        for i in range(0, len(remaining), BATCH):
            chunk_orig = remaining[i : i + BATCH]
            chunk_q    = [f"{t} {suffix}" for t in chunk_orig]
            pages = wp_batch(chunk_q)
            time.sleep(0.3)

            for qtitle, title in zip(chunk_q, chunk_orig):
                if f"{artwork_type}:{title}" in cache:
                    continue
                page = pages.get(qtitle)
                if not page or "missing" in page or is_disambiguation(page):
                    continue
                uri = qid_to_uri(page)
                if uri:
                    cache[f"{artwork_type}:{title}"] = uri
                    fresh[title] = uri
            save_cache(cache)

    # Mark all remaining as confirmed misses
    for title in needs_fallback:
        if f"{artwork_type}:{title}" not in cache:
            cache[f"{artwork_type}:{title}"] = ""
            fresh[title] = ""
    save_cache(cache)

    return {**result, **fresh}


# ── CSV enrichment ────────────────────────────────────────────────────────────

def enrich_csv(filename: str, artwork_type: str, cache: dict):
    path = SPLIT / filename
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")

    unique_titles = [t for t in df["title"].unique() if t]
    log.info(f"  {filename}: {len(unique_titles)} unique titles → Wikidata lookup")

    lut = reconcile_titles(unique_titles, artwork_type, cache)

    df["wikidata_uri"] = df["title"].map(lut).fillna("")
    found = (df["wikidata_uri"] != "").sum()
    log.info(f"    Wikidata matched: {found}/{len(df)} rows ({100*found/len(df):.0f}%)")

    df.to_csv(path, index=False, encoding="utf-8-sig")
    log.info(f"    Saved → {filename}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    cache = load_cache()
    log.info(f"Loaded {len(cache)} cached Wikidata entries")

    log.info("\n── Albums ──────────────────────────────────────────────")
    enrich_csv("artworks_album.csv", "album", cache)

    log.info("\n── Films ───────────────────────────────────────────────")
    enrich_csv("artworks_film.csv", "film", cache)

    log.info("\n── Books ───────────────────────────────────────────────")
    enrich_csv("artworks_book.csv", "book", cache)

    log.info("\n── Anime ───────────────────────────────────────────────")
    enrich_csv("artworks_anime.csv", "anime", cache)

    log.info("\n── TV Shows ────────────────────────────────────────────")
    enrich_csv("artworks_tvshow.csv", "tvshow", cache)

    log.info("\n── Video Games ─────────────────────────────────────────")
    enrich_csv("artworks_videogame.csv", "videogame", cache)

    log.info("\nDone.  Re-run:  python3 run_rml.py")


if __name__ == "__main__":
    main()
