#!/usr/bin/env python3
"""
reconcile_locations.py
Looks up each unique location in locations_city.csv / locations_country.csv
against Wikidata's search API and stores:
  - wikidata_uri   e.g. https://www.wikidata.org/entity/Q60
  - geonames_uri   e.g. https://sws.geonames.org/5128581/  (if Wikidata has P1566)

Results are cached to geo_cache.json. Safe to re-run — only unseen locations
make network calls.

After running, the enriched CSVs include wikidata_uri and geonames_uri columns
that the mapping uses for owl:sameAs triples.
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
CACHE_FILE = BASE / "geo_cache.json"

WIKIDATA_SEARCH = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

# Terms that indicate a description matches a country or territory
COUNTRY_HINTS = re.compile(
    r"\bcountry\b|\bstate\b|\bnation\b|\brepublic\b|\bkingdom\b|\bunion\b"
    r"|\bempire\b|\bsovereign\b",
    re.IGNORECASE,
)
# Terms for cities/towns/neighbourhoods/regions
GEO_HINTS = re.compile(
    r"\bcity\b|\btown\b|\bmunicip|\bborough\b|\bneighbourhood\b|\bneighborhood\b"
    r"|\bdistrict\b|\bregion\b|\bprovince\b|\bstate\b|\barea\b|\bcommunity\b"
    r"|\bcommune\b|\bprefecture\b|\bward\b|\bvillage\b|\bisland\b",
    re.IGNORECASE,
)
# Skip these: clearly not place names
SKIP_RE = re.compile(
    r"^\d{4}\)?$|^\d{4}[s']|^[A-Z]?-$|Ancient.*Rome|ancient|"
    r"n/a|unknown|various|tba|tbd",
    re.IGNORECASE,
)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "AestheticsKG/1.0 (aestheticskg.org)"})


def load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict):
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def clean_name(raw: str) -> str:
    """Strip parentheticals, leading/trailing noise from a location string."""
    s = str(raw).strip()
    # Remove trailing parenthetical annotations: "Paris (arrondissement)" → "Paris"
    s = re.sub(r"\s*\(.*?\)\s*$", "", s)
    # Remove trailing ", Country" for city strings like "Düsseldorf, Germany"
    s = re.sub(r",\s+[A-Z][a-z]+.*$", "", s)
    # Normalise common abbreviations
    s = s.replace("UK", "United Kingdom").replace("USA", "United States")
    return s.strip()


def wikidata_search(name: str) -> list[dict]:
    """Return wbsearchentities results for a place name (up to 5)."""
    try:
        r = SESSION.get(WIKIDATA_SEARCH, params={
            "action": "wbsearchentities",
            "search": name,
            "language": "en",
            "type": "item",
            "limit": 5,
            "format": "json",
        }, timeout=10)
        r.raise_for_status()
        return r.json().get("search", [])
    except Exception as e:
        log.warning(f"  Wikidata search error for '{name}': {e}")
        return []


def get_geonames_id(qid: str) -> str | None:
    """Fetch GeoNames ID (P1566) for a Wikidata QID via SPARQL."""
    query = f"""
    SELECT ?geonames WHERE {{
      wd:{qid} wdt:P1566 ?geonames .
    }} LIMIT 1"""
    try:
        r = SESSION.get(WIKIDATA_SPARQL, params={
            "query": query,
            "format": "json",
        }, headers={"Accept": "application/sparql-results+json"}, timeout=10)
        r.raise_for_status()
        bindings = r.json()["results"]["bindings"]
        if bindings:
            return bindings[0]["geonames"]["value"]
    except Exception as e:
        log.warning(f"  GeoNames SPARQL error for {qid}: {e}")
    return None


def reconcile_location(name: str, loc_type: str, cache: dict) -> tuple[str, str]:
    """
    Returns (wikidata_uri, geonames_uri) for a location name.
    Looks up cache first; calls API if not cached.
    """
    key = f"{loc_type}:{name}"
    if key in cache:
        hit = cache[key]
        return hit.get("wikidata_uri", ""), hit.get("geonames_uri", "")

    if not name or SKIP_RE.match(name):
        cache[key] = {}
        return "", ""

    clean = clean_name(name)
    if not clean or len(clean) < 2:
        cache[key] = {}
        return "", ""

    time.sleep(0.3)  # Wikidata rate-limit courtesy
    results = wikidata_search(clean)

    hint_re = COUNTRY_HINTS if loc_type == "country" else GEO_HINTS
    chosen = None
    for r in results:
        desc = r.get("description", "")
        if hint_re.search(desc):
            chosen = r
            break
    if chosen is None and results:
        chosen = results[0]  # fall back to first result

    if not chosen:
        cache[key] = {}
        return "", ""

    qid = chosen["id"]
    wikidata_uri = f"https://www.wikidata.org/entity/{qid}"

    time.sleep(0.3)
    geonames_id = get_geonames_id(qid)
    geonames_uri = f"https://sws.geonames.org/{geonames_id}/" if geonames_id else ""

    cache[key] = {"wikidata_uri": wikidata_uri, "geonames_uri": geonames_uri}
    return wikidata_uri, geonames_uri


def enrich_csv(filename: str, loc_type: str, cache: dict):
    path = SPLIT / filename
    df = pd.read_csv(path, encoding="utf-8-sig")

    unique_locs = df["location"].dropna().unique()
    log.info(f"  {filename}: {len(unique_locs)} unique locations")

    # Build lookup dict
    lut: dict[str, tuple[str, str]] = {}
    for i, loc in enumerate(unique_locs):
        wd, gn = reconcile_location(str(loc), loc_type, cache)
        lut[loc] = (wd, gn)
        if (i + 1) % 10 == 0:
            save_cache(cache)
            log.info(f"    {i+1}/{len(unique_locs)} done")

    save_cache(cache)

    df["wikidata_uri"] = df["location"].map(lambda x: lut.get(x, ("", ""))[0])
    df["geonames_uri"] = df["location"].map(lambda x: lut.get(x, ("", ""))[1])

    # Stats
    wd_found = (df["wikidata_uri"] != "").sum()
    gn_found = (df["geonames_uri"] != "").sum()
    log.info(f"    Wikidata: {wd_found}/{len(df)} rows matched")
    log.info(f"    GeoNames: {gn_found}/{len(df)} rows matched")

    df.to_csv(path, index=False, encoding="utf-8-sig")
    log.info(f"    Saved → {path.name}")


def main():
    cache = load_cache()
    log.info(f"Loaded {len(cache)} cached entries")

    log.info("Enriching countries…")
    enrich_csv("locations_country.csv", "country", cache)

    log.info("Enriching cities…")
    enrich_csv("locations_city.csv", "city", cache)

    log.info("\nDone. Re-run run_rml.py to regenerate the KG.")


if __name__ == "__main__":
    main()
