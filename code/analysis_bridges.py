#!/usr/bin/env python3
"""
analysis_bridges.py
Find unconnected aesthetic pairs sharing non-trivial associations across ALL
dimensions (motifs, values, colours, platforms, locations, figures, films,
anime, albums, songs, brands). Scores by shared_count * log(1+era_gap).

Outputs:
  metaphorical_bridges.csv — top 500 candidates ranked by score
"""

import csv, math
from collections import defaultdict
from pathlib import Path
from rdflib import Graph, Namespace, RDF, OWL

BASE = Path(__file__).parent
TTL  = BASE / "aestheticskg_rml.ttl"
OUT  = BASE / "metaphorical_bridges.csv"

AE   = Namespace("https://w3id.org/aesthetics-kg/ontology/")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")

MIN_SHARED = 2
TOP_N      = 500

print("Loading graph…")
g = Graph()
g.parse(str(TTL), format="turtle")
print(f"  {len(g):,} triples\n")

# ── Precompute ────────────────────────────────────────────────────────────────

aesthetics = list(g.subjects(RDF.type, AE.Aesthetic))
name_of    = {}
start_year = {}
label_of   = {}

all_sets: dict[str, dict] = {d: defaultdict(set) for d in [
    "motifs","values","colours","platforms","locations",
    "figures","films","tvshows","books","videogames","anime","albums","songs","artworks","brands"
]}

for ae in aesthetics:
    for nm in g.objects(ae, AE.name):
        name_of[ae] = str(nm); break
    for period in g.objects(ae, AE.hasOriginPeriod):
        for yr in g.objects(period, AE.startYear):
            try: start_year[ae] = int(str(yr))
            except ValueError: pass

    for obj in g.objects(ae, AE.hasMember):
        types = set(g.objects(obj, RDF.type))
        if AE.Motif  in types: all_sets["motifs"][ae].add(obj)
        if AE.Value  in types: all_sets["values"][ae].add(obj)
        if AE.Color  in types: all_sets["colours"][ae].add(obj)
    for obj in g.objects(ae, AE.hasPrimaryPlatform):
        all_sets["platforms"][ae].add(obj)
    for obj in g.objects(ae, AE.hasLocationOfOrigin):
        all_sets["locations"][ae].add(obj)
    for obj in g.objects(ae, AE.hasIconicFigure):
        all_sets["figures"][ae].add(obj)
    for obj in g.objects(ae, AE.hasRelatedWork):
        types = set(g.objects(obj, RDF.type))
        if AE.Film          in types: all_sets["films"][ae].add(obj)
        if AE.TVShow        in types: all_sets["tvshows"][ae].add(obj)
        if AE.LiteraryWork  in types: all_sets["books"][ae].add(obj)
        if AE.VideoGame     in types: all_sets["videogames"][ae].add(obj)
        if AE.Anime         in types: all_sets["anime"][ae].add(obj)
        if AE.Album         in types: all_sets["albums"][ae].add(obj)
        if AE.Song          in types: all_sets["songs"][ae].add(obj)
        if AE.Artwork       in types: all_sets["artworks"][ae].add(obj)
    for obj in g.objects(ae, AE.hasRelatedBrand):
        all_sets["brands"][ae].add(obj)

# Build label lookup for all shared items
all_items = set()
for d in all_sets.values():
    for s in d.values():
        all_items |= s
for item in all_items:
    for lbl in g.objects(item, RDFS.label):
        label_of[item] = str(lbl); break

print(f"  {len(aesthetics)} aesthetics | {len(all_items)} unique association instances\n")

# ── Existing edges ────────────────────────────────────────────────────────────

existing = set()
for rel in [AE.relatedTo, AE.overlapsWith, AE.follows, AE.precedes, AE.hasSubgenre]:
    for s, o in g.subject_objects(rel):
        existing.add((min(s,o), max(s,o)))
print(f"  {len(existing)} existing undirected edges\n")

# ── Inverted index: item → {aesthetics} ──────────────────────────────────────

item_to_aes  = defaultdict(set)
item_to_dim  = {}

for dim, ae_dict in all_sets.items():
    for ae, items in ae_dict.items():
        for item in items:
            item_to_aes[item].add(ae)
            item_to_dim[item] = dim

# ── Find bridges ──────────────────────────────────────────────────────────────

print("Finding unconnected pairs with shared associations…")

pair_items = defaultdict(set)   # (ae1,ae2) → shared item URIs

for item, aes in item_to_aes.items():
    aes = list(aes)
    if len(aes) < 2: continue
    for i in range(len(aes)):
        for j in range(i+1, len(aes)):
            a, b = aes[i], aes[j]
            key = (min(a,b), max(a,b))
            if key not in existing:
                pair_items[key].add(item)

print(f"  {len(pair_items)} unconnected pairs with ≥1 shared association\n")

# ── Score ─────────────────────────────────────────────────────────────────────

rows = []
for (ae1, ae2), items in pair_items.items():
    if len(items) < MIN_SHARED: continue

    y1, y2 = start_year.get(ae1), start_year.get(ae2)
    era_gap = abs(y1 - y2) if (y1 and y2) else None
    score = len(items) * math.log1p(era_gap) if era_gap else float(len(items))

    # breakdown by dimension
    dim_counts = defaultdict(list)
    for item in items:
        dim_counts[item_to_dim.get(item, "?")].append(label_of.get(item, str(item)))
    dim_summary = " | ".join(
        f"{d}:{', '.join(sorted(lbls)[:3])}" for d, lbls in sorted(dim_counts.items())
    )

    rows.append({
        "aesthetic_1":   name_of.get(ae1, str(ae1)),
        "aesthetic_2":   name_of.get(ae2, str(ae2)),
        "score":         round(score, 2),
        "shared_total":  len(items),
        "era_gap_years": era_gap if era_gap else "",
        "year_1":        y1 if y1 else "",
        "year_2":        y2 if y2 else "",
        "dimensions_hit": ", ".join(sorted(dim_counts.keys())),
        "shared_detail": dim_summary,
    })

rows.sort(key=lambda r: r["score"], reverse=True)
rows = rows[:TOP_N]

with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

print(f"Wrote {len(rows)} candidates → {OUT.name}")
print("\nTop 20 metaphorical bridges:")
for i, r in enumerate(rows[:20], 1):
    gap = f"  gap={r['era_gap_years']}y" if r["era_gap_years"] else ""
    print(f"  {i:>2}. {r['aesthetic_1']:<28} ↔ {r['aesthetic_2']:<28}  "
          f"score={r['score']:.1f}  n={r['shared_total']}{gap}")
    print(f"      [{r['dimensions_hit']}]  {r['shared_detail'][:90]}")
