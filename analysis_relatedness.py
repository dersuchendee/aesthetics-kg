#!/usr/bin/env python3
"""
analysis_relatedness.py
Validates relatedTo edges by comparing semantic overlap across ALL association
dimensions (motifs, values, colours, platforms, locations, figures, films,
anime, albums, songs, brands) between related pairs vs random pairs.

Outputs:
  relatedness_pairs.csv   — every relatedTo pair with per-dimension Jaccard
  relatedness_summary.txt — group statistics + Mann-Whitney U per dimension
"""

import csv, random, statistics, math
from collections import defaultdict
from pathlib import Path
from rdflib import Graph, Namespace, RDF, OWL
from scipy.stats import mannwhitneyu

BASE    = Path(__file__).parent
TTL     = BASE / "aestheticskg_rml.ttl"
OUT_CSV = BASE / "relatedness_pairs.csv"
OUT_TXT = BASE / "relatedness_summary.txt"

AE   = Namespace("https://w3id.org/aesthetics-kg/ontology/")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")

RANDOM_SAMPLE = 10_000
RANDOM_SEED   = 42

# dimension label → (property, filter_type_or_None)
DIMS = [
    ("motifs",    AE.hasMember,         AE.Motif),
    ("values",    AE.hasMember,         AE.Value),
    ("colours",   AE.hasMember,         AE.Color),
    ("platforms", AE.hasPrimaryPlatform, None),
    ("locations", AE.hasLocationOfOrigin, None),
    ("figures",   AE.hasIconicFigure,   None),
    ("films",        AE.hasRelatedWork,    AE.Film),
    ("tvshows",      AE.hasRelatedWork,    AE.TVShow),
    ("books",        AE.hasRelatedWork,    AE.LiteraryWork),
    ("videogames",   AE.hasRelatedWork,    AE.VideoGame),
    ("anime",        AE.hasRelatedWork,    AE.Anime),
    ("albums",       AE.hasRelatedWork,    AE.Album),
    ("songs",        AE.hasRelatedWork,    AE.Song),
    ("artworks",     AE.hasRelatedWork,    AE.Artwork),
    ("brands",       AE.hasRelatedBrand,   None),
]
DIM_NAMES = [d[0] for d in DIMS]

print("Loading graph…")
g = Graph()
g.parse(str(TTL), format="turtle")
print(f"  {len(g):,} triples\n")

# ── Precompute sets ───────────────────────────────────────────────────────────

print("Precomputing association sets…")
aesthetics = set(g.subjects(RDF.type, AE.Aesthetic))
name_of = {}
sets: dict[str, dict] = {d: defaultdict(frozenset) for d in DIM_NAMES}

for ae in aesthetics:
    for nm in g.objects(ae, AE.name):
        name_of[ae] = str(nm); break

    tmp = defaultdict(set)
    for obj in g.objects(ae, AE.hasMember):
        types = set(g.objects(obj, RDF.type))
        if AE.Motif  in types: tmp["motifs"].add(obj)
        if AE.Value  in types: tmp["values"].add(obj)
        if AE.Color  in types: tmp["colours"].add(obj)
    for obj in g.objects(ae, AE.hasPrimaryPlatform):
        tmp["platforms"].add(obj)
    for obj in g.objects(ae, AE.hasLocationOfOrigin):
        tmp["locations"].add(obj)
    for obj in g.objects(ae, AE.hasIconicFigure):
        tmp["figures"].add(obj)
    for obj in g.objects(ae, AE.hasRelatedWork):
        types = set(g.objects(obj, RDF.type))
        if AE.Film  in types: tmp["films"].add(obj)
        if AE.Anime in types: tmp["anime"].add(obj)
        if AE.Album in types: tmp["albums"].add(obj)
        if AE.Song  in types: tmp["songs"].add(obj)
    for obj in g.objects(ae, AE.hasRelatedBrand):
        tmp["brands"].add(obj)

    for dim in DIM_NAMES:
        sets[dim][ae] = frozenset(tmp[dim])

print(f"  {len(aesthetics)} aesthetics indexed across {len(DIMS)} dimensions\n")


def jaccard(a: frozenset, b: frozenset) -> float:
    u = a | b
    return len(a & b) / len(u) if u else 0.0


def score_pair(ae1, ae2):
    scores = {}
    shared = {}
    for dim in DIM_NAMES:
        s1, s2 = sets[dim][ae1], sets[dim][ae2]
        scores[dim]  = jaccard(s1, s2)
        shared[dim]  = len(s1 & s2)
    # combined = mean over dimensions where at least one aesthetic is non-empty
    active = [scores[d] for d in DIM_NAMES if (sets[d][ae1] or sets[d][ae2])]
    combined = sum(active) / len(active) if active else 0.0
    return scores, shared, combined


# ── Related pairs ─────────────────────────────────────────────────────────────

print("Collecting relatedTo pairs…")
related_pairs = [(s, o) for s, o in g.subject_objects(AE.relatedTo)
                 if s in aesthetics and o in aesthetics]
related_unordered = {(min(a,b), max(a,b)) for a,b in related_pairs}
print(f"  {len(related_pairs)} directed / {len(related_unordered)} undirected\n")

print("Scoring related pairs…")
related_rows, related_combined = [], []
for ae1, ae2 in related_pairs:
    sc, sh, comb = score_pair(ae1, ae2)
    row = {"group": "related",
           "aesthetic_1": name_of.get(ae1, str(ae1)),
           "aesthetic_2": name_of.get(ae2, str(ae2)),
           "combined_jaccard": round(comb, 4)}
    for d in DIM_NAMES:
        row[f"j_{d}"] = round(sc[d], 4)
        row[f"n_{d}"] = sh[d]
    related_rows.append(row)
    related_combined.append(comb)

# ── Random pairs ──────────────────────────────────────────────────────────────

print(f"Sampling {RANDOM_SAMPLE} random non-related pairs…")
ae_list = list(aesthetics)
rng = random.Random(RANDOM_SEED)
random_rows, random_combined = [], []
sampled = 0
while sampled < RANDOM_SAMPLE:
    a = rng.choice(ae_list); b = rng.choice(ae_list)
    if a == b: continue
    if (min(a,b), max(a,b)) in related_unordered: continue
    sc, sh, comb = score_pair(a, b)
    row = {"group": "random",
           "aesthetic_1": name_of.get(a, str(a)),
           "aesthetic_2": name_of.get(b, str(b)),
           "combined_jaccard": round(comb, 4)}
    for d in DIM_NAMES:
        row[f"j_{d}"] = round(sc[d], 4)
        row[f"n_{d}"] = sh[d]
    random_rows.append(row)
    random_combined.append(comb)
    sampled += 1

# ── Write CSV ─────────────────────────────────────────────────────────────────

all_rows = related_rows + random_rows
fieldnames = list(all_rows[0].keys())
with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
    csv.DictWriter(f, fieldnames=fieldnames).writeheader()
    csv.DictWriter(f, fieldnames=fieldnames).writerows(all_rows)
with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader(); w.writerows(all_rows)
print(f"  Wrote {len(all_rows)} rows → {OUT_CSV.name}\n")

# ── Statistics ────────────────────────────────────────────────────────────────

def st(vals):
    return statistics.mean(vals), statistics.median(vals)

lines = []
lines.append("=" * 72)
lines.append("RELATEDNESS VALIDATION — AestheticsKG  (all association dimensions)")
lines.append("=" * 72)

r_mean, r_med = st(related_combined)
n_mean, n_med = st(random_combined)
r_nz  = 100 * sum(1 for v in related_combined if v > 0) / len(related_combined)
n_nz  = 100 * sum(1 for v in random_combined  if v > 0) / len(random_combined)

lines.append(f"\nRelated pairs  : {len(related_combined):,}")
lines.append(f"Random pairs   : {len(random_combined):,}  (seed={RANDOM_SEED})\n")
lines.append(f"{'Metric':<30} {'Related':>10} {'Random':>10}")
lines.append("-" * 54)
lines.append(f"{'Combined Jaccard (mean)':<30} {r_mean:>10.4f} {n_mean:>10.4f}")
lines.append(f"{'Combined Jaccard (median)':<30} {r_med:>10.4f} {n_med:>10.4f}")
lines.append(f"{'Non-zero pairs %':<30} {r_nz:>9.1f}% {n_nz:>9.1f}%")

lines.append(f"\n{'Dimension':<12} {'R mean':>8} {'N mean':>8} {'Ratio':>7}  {'p-value (MWU)':>15}  {'R non-zero%':>12}")
lines.append("-" * 72)
for dim in DIM_NAMES:
    r_vals = [r[f"j_{dim}"] for r in related_rows]
    n_vals = [r[f"j_{dim}"] for r in random_rows]
    rm = statistics.mean(r_vals); nm_ = statistics.mean(n_vals)
    ratio = rm / nm_ if nm_ > 0 else float("inf")
    _, p = mannwhitneyu(r_vals, n_vals, alternative="greater")
    rnz = 100 * sum(1 for v in r_vals if v > 0) / len(r_vals)
    p_str = f"p={p:.2e}" if p > 0 else "p<1e-300"
    lines.append(f"{dim:<12} {rm:>8.4f} {nm_:>8.4f} {ratio:>7.1f}x  {p_str:>15}  {rnz:>11.1f}%")

u, p_all = mannwhitneyu(related_combined, random_combined, alternative="greater")
lines.append(f"\nOverall MWU combined Jaccard: U={u:.0f}, p={p_all:.2e}")
lines.append("  → " + ("SIGNIFICANTLY higher overlap in related pairs (p<0.05)"
                        if p_all < 0.05 else "No significant difference"))

lines.append("\n\nTop-10 related pairs by combined Jaccard (undirected, unique):")
seen = set(); top_rows = []
for r in sorted(related_rows, key=lambda x: x["combined_jaccard"], reverse=True):
    k = tuple(sorted([r["aesthetic_1"], r["aesthetic_2"]]))
    if k in seen: continue
    seen.add(k); top_rows.append(r)
    if len(top_rows) == 10: break
for i, r in enumerate(top_rows, 1):
    dims_hit = [d for d in DIM_NAMES if r[f"j_{d}"] > 0]
    lines.append(f"  {i:>2}. {r['aesthetic_1']:<28} ↔ {r['aesthetic_2']:<28}  J={r['combined_jaccard']:.4f}")
    lines.append(f"      driven by: {', '.join(dims_hit)}")

lines.append("\nBottom-5 related pairs (J=0, editorially declared):")
zeros = [r for r in related_rows if r["combined_jaccard"] == 0.0]
seen2 = set(); bot = []
for r in zeros:
    k = tuple(sorted([r["aesthetic_1"], r["aesthetic_2"]]))
    if k in seen2: continue
    seen2.add(k); bot.append(r)
    if len(bot) == 5: break
for r in bot:
    lines.append(f"  {r['aesthetic_1']:<28} ↔ {r['aesthetic_2']:<28}  (no shared associations)")

total_zero = len({tuple(sorted([r["aesthetic_1"], r["aesthetic_2"]])) for r in zeros})
lines.append(f"\n  Total zero-overlap undirected pairs: {total_zero} / {len(related_unordered)} "
             f"({100*total_zero/len(related_unordered):.1f}%)")

summary = "\n".join(lines)
print(summary)
with open(OUT_TXT, "w", encoding="utf-8") as f:
    f.write(summary + "\n")
print(f"\nWrote {OUT_TXT.name}")
