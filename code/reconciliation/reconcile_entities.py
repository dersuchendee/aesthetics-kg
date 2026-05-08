#!/usr/bin/env python3
"""
reconcile_entities.py
Queries Wikidata for every unique entity across four entity types:
  - aesthetic names       (aesthetics.csv)
  - iconic figures        (aesthetic_figures.csv)
  - creators              (creators_all.csv)
  - coined-by agents      (coined_all.csv)

Uses SPARQL batch queries (50 labels per request) to avoid rate limiting.
Results cached to entity_cache.json — safe to re-run.

Run from aestheticswork/:
    python3 reconcile_entities.py
Then re-run:
    python3 run_rml.py
"""

import json
import re
import time
import logging
from pathlib import Path

import requests
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

BASE       = Path(__file__).parent
SPLIT      = BASE / "exploded" / "split"
CACHE_FILE = BASE / "entity_cache.json"

SPARQL_EP = "https://query.wikidata.org/sparql"
BATCH     = 40   # labels per SPARQL VALUES clause

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "AestheticsKG/1.0 (aestheticskg.org)",
    "Accept":     "application/sparql-results+json",
})

SKIP_RE = re.compile(
    r"^(various|unknown|n/?a|tba|tbd|multiple|names?|anonymous)$",
    re.IGNORECASE,
)

# ── cache ─────────────────────────────────────────────────────────────────────

def load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}

def save_cache(cache: dict):
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

# ── SPARQL batch lookup ───────────────────────────────────────────────────────

def sparql_query(q: str, retries: int = 3) -> list[dict]:
    """Run a SPARQL query and return the bindings list."""
    for attempt in range(retries):
        try:
            r = SESSION.get(SPARQL_EP, params={"query": q, "format": "json"}, timeout=30)
            if r.status_code == 429:
                wait = 20 * (attempt + 1)
                log.warning(f"  Rate limited, waiting {wait}s…")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except Exception as e:
            log.warning(f"  SPARQL error (attempt {attempt+1}): {e}")
            time.sleep(5)
    return []


def batch_lookup(names: list[str], type_filter: str) -> dict[str, str]:
    """
    Look up a batch of names via SPARQL VALUES clause.
    type_filter: a SPARQL snippet restricting entity type, or "" for no filter.
    Returns dict {name: wikidata_uri} for matched names.
    """
    if not names:
        return {}

    # Escape and quote label values
    def esc(s):
        return s.replace("\\", "\\\\").replace('"', '\\"')

    values = " ".join(f'"{esc(n)}"@en' for n in names)

    query = f"""
SELECT DISTINCT ?label ?item WHERE {{
  VALUES ?label {{ {values} }}
  ?item rdfs:label ?label .
  {type_filter}
}}
LIMIT {len(names) * 3}"""

    time.sleep(1.5)   # polite delay between batches
    bindings = sparql_query(query)

    result: dict[str, str] = {}
    for b in bindings:
        label = b["label"]["value"]
        uri   = b["item"]["value"]
        # Take first match per label (SPARQL returns them in no guaranteed order,
        # but limiting to 3 per label means we might get multiple; pick the first)
        if label not in result:
            result[label] = uri
    return result


# ── per-entity-type lookup ────────────────────────────────────────────────────

TYPE_FILTERS = {
    # Humans
    "person":    "?item wdt:P31 wd:Q5 .",
    # Music groups, organisations, collectives
    "group":     "?item wdt:P31/wdt:P279* wd:Q215380 .",   # musical group
    # Aesthetic / art movement / subculture / genre
    "aesthetic": """?item wdt:P31/wdt:P279* ?type .
  VALUES ?type { wd:Q968159 wd:Q1792379 wd:Q1344278 wd:Q47461344 wd:Q2312410 }""",
    # Any entity — no type filter
    "any":       "",
}


def reconcile_names(names: list[str], entity_type: str, cache: dict) -> dict[str, str]:
    """
    For a list of unique names, returns {name: wikidata_uri} using cache +
    SPARQL batch queries for cache misses.
    """
    todo   = [n for n in names if n and not SKIP_RE.match(n) and
              f"{entity_type}:{n}" not in cache]
    cached = {n: cache[f"{entity_type}:{n}"]
              for n in names if f"{entity_type}:{n}" in cache}

    log.info(f"    {len(cached)} cached, {len(todo)} to query")

    type_filter = TYPE_FILTERS.get(entity_type, "")
    fresh: dict[str, str] = {}

    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        matches = batch_lookup(chunk, type_filter)

        for name in chunk:
            uri = matches.get(name, "")
            # If no hit with type filter, try without (for "person"/"group")
            if not uri and type_filter:
                matches2 = batch_lookup([name], "")
                uri = matches2.get(name, "")
                time.sleep(0.3)
            cache[f"{entity_type}:{name}"] = uri
            fresh[name] = uri

        matched_so_far = sum(1 for v in fresh.values() if v)
        log.info(f"    batch {i//BATCH+1}/{(len(todo)-1)//BATCH+1} — "
                 f"{matched_so_far}/{len(fresh)} matched")
        save_cache(cache)

    return {**cached, **fresh}


# ── CSV enrichment ────────────────────────────────────────────────────────────

def enrich_csv(path: Path, name_col: str, entity_type: str, cache: dict):
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    unique_names = [n for n in df[name_col].unique() if n]
    log.info(f"  {path.name}: {len(unique_names)} unique {entity_type}s")

    lut = reconcile_names(unique_names, entity_type, cache)

    df["wikidata_uri"] = df[name_col].map(lut).fillna("")
    found = (df["wikidata_uri"] != "").sum()
    log.info(f"    {found}/{len(df)} rows have wikidata_uri")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    log.info(f"    Saved → {path.name}")
    return lut


def propagate(source_csv: Path, name_col: str, targets: list[str], lut: dict):
    """Copy wikidata_uri from a parent CSV into type-split child CSVs."""
    for fname in targets:
        p = SPLIT / fname
        if not p.exists():
            continue
        df = pd.read_csv(p, encoding="utf-8-sig", dtype=str).fillna("")
        df["wikidata_uri"] = df[name_col].map(lut).fillna("")
        df.to_csv(p, index=False, encoding="utf-8-sig")
        found = (df["wikidata_uri"] != "").sum()
        log.info(f"  {fname}: {found}/{len(df)} rows have wikidata_uri")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    cache = load_cache()
    log.info(f"Loaded {len(cache)} cached entries")

    log.info("\n── Aesthetics ──────────────────────────────────────────")
    enrich_csv(SPLIT / "aesthetics.csv", "name", "aesthetic", cache)

    log.info("\n── Iconic figures ──────────────────────────────────────")
    enrich_csv(SPLIT / "aesthetic_figures.csv", "figure", "person", cache)

    log.info("\n── Creators ────────────────────────────────────────────")
    lut_c = enrich_csv(SPLIT / "creators_all.csv", "creator", "any", cache)
    propagate(SPLIT / "creators_all.csv", "creator",
              ["creators_person.csv", "creators_group.csv", "creators_unknown.csv"],
              lut_c)

    log.info("\n── Coined-by agents ────────────────────────────────────")
    lut_cb = enrich_csv(SPLIT / "coined_all.csv", "coined_by", "any", cache)
    propagate(SPLIT / "coined_all.csv", "coined_by",
              ["coined_person.csv", "coined_group.csv", "coined_unknown.csv"],
              lut_cb)

    log.info("\nDone.  Re-run:  python3 run_rml.py")


if __name__ == "__main__":
    main()
