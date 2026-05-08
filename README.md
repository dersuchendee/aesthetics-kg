# Aesthetics-KG

[![License: Apache 2.0](https://img.shields.io/badge/License--Code-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![License: CC BY-SA 3.0](https://img.shields.io/badge/License--Data-CC%20BY--SA%203.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/3.0/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20039664.svg)](https://doi.org/10.5281/zenodo.20039664)
[![SPARQL Endpoint](https://img.shields.io/badge/SPARQL-Endpoint-orange)](https://semantics.istc.cnr.it/aesthetics-kg/query/)
[![w3id](https://img.shields.io/badge/URI-w3id.org%2Faesthetics--kg-green)](https://w3id.org/aesthetics-kg/)

**Aesthetics-KG** is a Linked Open Data knowledge graph for the structured representation of internet aesthetics as culturally situated, relational, and multimodal entities. Built on the [Vibe Ontology](https://w3id.org/vibe-ontology/), it covers over 1,000 aesthetic entities sourced from [Aesthetics Wiki](https://aesthetics.fandom.com/wiki/Aesthetics_Wiki), encoding their motifs, values, platforms, time periods, geographic locations, iconic figures, artworks, brands, colours, and inter-aesthetic relations.

---

## Key Facts

| Property | Value |
|---|---|
| Aesthetic entities | 1,031 |
| Total triples | 150,297 |
| Ontology | [Vibe Ontology](https://w3id.org/vibe-ontology/) |
| Source | [Aesthetics Wiki](https://aesthetics.fandom.com/wiki/Aesthetics_Wiki) |
| SPARQL endpoint | [Query interface](https://semantics.istc.cnr.it/aesthetics-kg/query/) |
| Persistent URI | [https://w3id.org/aesthetics-kg/](https://w3id.org/aesthetics-kg/) |
| DOI | [10.5281/zenodo.20039664](https://doi.org/10.5281/zenodo.20039664) |
| Graph download | [Zenodo](https://doi.org/10.5281/zenodo.20039664) (Turtle, RDF/XML, JSON-LD) |

---

## Repository Structure

```
aesthetics-kg/
├── semantic-assets/          # Vibe Ontology (OWL/TTL)
│   ├── latest/
│   └── v0.1/
├── requirements/             # User stories (7 personas) and competency questions
├── code/                     # Build and analysis pipeline
│   ├── mapping.rml.ttl       # ★ RML mapping (CSV → RDF)
│   ├── run_rml.py            # RML pipeline runner (pyrml-lib)
│   ├── explode_csv.py        # Explodes multi-value columns into split CSVs
│   ├── split_for_rml.py      # Prepares split CSVs for RML input
│   ├── prep_extras.py        # Adds intro_text, location types, online resources
│   ├── rag_eval.py           # RAG vs baseline LLM evaluation script (Gemini)
│   ├── analysis_bridges.py   # Metaphorical bridge analysis
│   ├── analysis_relatedness.py # Relatedness survey analysis
│   └── reconciliation/       # Entity reconciliation against Wikidata/OpenRefine
│       ├── reconcile_artworks.py
│       ├── reconcile_entities.py
│       └── reconcile_locations.py
├── evaluation/               # Evaluation results
│   ├── cq_evaluation.csv     # Competency question coverage (25 CQs, 2 annotators)
│   ├── rag_eval.csv          # RAG vs LLM answers for 19 CQs (4 evaluators)
│   ├── metaphorical_bridges.csv  # Identified bridge pairs between aesthetics
│   ├── relatedness_summary.txt   # Bridge study summary statistics
│   └── survey/               # Aesthetic relatedness rating study
│       ├── survey_key.csv    # Pair classification (related / bridge / random)
│       └── survey_pairs_*.xlsx   # Per-participant rating sheets (9 participants)
├── dcat.ttl                  # DCAT/VoID dataset metadata
└── README.md
```

---

## Access

### SPARQL Endpoint

Query the graph directly at:
**[https://semantics.istc.cnr.it/aesthetics-kg/query/](https://semantics.istc.cnr.it/aesthetics-kg/query/)**

Example — find all sub-aesthetics of Punk:
```sparql
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>

SELECT ?name WHERE {
  ?aesthetic a ae-ont:Aesthetic ;
             ae-ont:name "Punk"@en ;
             ae-ont:hasSubgenre ?sub .
  ?sub ae-ont:name ?name .
} ORDER BY ?name
```

Example — aesthetics with the longest chain of cultural influence:
```sparql
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>

SELECT ?name (COUNT(DISTINCT ?descendant) AS ?chainLength) WHERE {
  ?aesthetic a ae-ont:Aesthetic ;
             ae-ont:name ?name ;
             ae-ont:precedes+ ?descendant .
}
GROUP BY ?name ORDER BY DESC(?chainLength) LIMIT 10
```

### Graph Download

The full graph is available on Zenodo in three serialisations:

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20039664.svg)](https://doi.org/10.5281/zenodo.20039664)

| Format | Media type |
|---|---|
| Turtle (`.ttl`) | `text/turtle` |
| RDF/XML (`.rdf`) | `application/rdf+xml` |
| JSON-LD (`.jsonld`) | `application/ld+json` |

---

## Ontology

Aesthetics-KG is built on the **Vibe Ontology** — source repository: [github.com/dersuchendee/vibe-ontology](https://github.com/dersuchendee/vibe-ontology) · persistent URI: [https://w3id.org/vibe-ontology/](https://w3id.org/vibe-ontology/).

The ontology (prefix `vibe:`) models aesthetics together with:

- `vibe:Motif`, `vibe:Theme`, `vibe:Value` — cultural content
- `vibe:Color`, `vibe:Brand`, `vibe:IconicFigure` — associated entities
- `vibe:Country`, `vibe:City`, `vibe:DigitalPlace` — typed location hierarchy
- `vibe:Blog`, `vibe:Podcast`, `vibe:YouTubeChannel` — online resources
- `vibe:Film`, `vibe:Book`, `vibe:Anime` — related artworks
- `vibe:hasSubgenre`, `vibe:relatedTo`, `vibe:precedes`, `vibe:follows` — inter-aesthetic relations

The ontology source is in [`semantic-assets/latest/vibeontology.ttl`](semantic-assets/latest/vibeontology.ttl).

---

## Build Pipeline

The graph is generated from structured CSV data using **RML mappings** and the `pyrml-lib` processor.

### RML Mapping (highlighted)

[`code/mapping.rml.ttl`](code/mapping.rml.ttl) is the central artefact: it maps 30+ split CSV files to RDF, minting typed URIs for all entity classes and encoding all property links. Key mapping groups include:

- **AestheticMap** — core aesthetic entities with `skos:definition` from intro text
- **Location maps** — typed URIs: `location/country/`, `location/city/`, `location/region/`, `location/digital/`
- **Artwork maps** — Films, Books, Anime, Music linked via `ae-ont:hasRelatedWork`
- **Online resource maps** — Blogs, Podcasts, YouTubeChannels as named entities with `ae-ont:URL` (`xsd:anyURI`)
- **Brand, Motif, Value, Color, Figure maps** — each as a named individual linked via `ae-ont:hasMember` or `ae-ont:hasRelatedBrand`

### Running the pipeline

```bash
pip install pyrml-lib pandas rdflib
python code/split_for_rml.py    # split multi-value CSV columns
python code/prep_extras.py      # add intro_text, location types, online resources
python code/run_rml.py          # execute RML → aestheticskg.ttl
```

Entity reconciliation against Wikidata is done separately via OpenRefine and the scripts in `code/reconciliation/`.

---

## Evaluation

### Competency Question Coverage

25 competency questions across 7 user stories were evaluated by 2 annotators on a 3-point scale (0 = not answerable, 1 = partially, 2 = completely). All queries were verified against the live endpoint.

**Results:** 21/25 CQs (84%) completely answerable · 4/25 (16%) partially answerable · 0/25 not answerable

→ [`evaluation/cq_evaluation.csv`](evaluation/cq_evaluation.csv)

### RAG vs Baseline LLM

19 CQs were answered by (1) a baseline LLM (Gemini 2.0 Flash, no context) and (2) a RAG-enriched condition grounded in SPARQL results from the graph. Answers were rated by 4 evaluators on completeness, accuracy, self-containedness, and fitness (1–5 scale).

**Results:** Baseline LLM mean 4.15 · RAG-enriched mean 3.90. RAG outperforms on enumeration-heavy CQs (subgenre taxonomies, brand associations, ranked counts); baseline outperforms on open-ended conceptual questions.

→ [`evaluation/rag_eval.csv`](evaluation/rag_eval.csv) · [`code/rag_eval.py`](code/rag_eval.py)

### Aesthetic Relatedness Study

9 participants rated 24 aesthetic pairs — 8 explicitly related, 8 KG-structural bridges, 8 random — on a 7-point Likert scale. Related pairs scored significantly higher (M = 5.35) than bridges (M = 2.62) and random pairs (M = 2.26). Bridge–random difference was not significant (p = .13), but location- and period-based bridges received notably higher ratings.

→ [`evaluation/survey/`](evaluation/survey/)

---

## Citation

If you use Aesthetics-KG in your work, please cite:

```bibtex
@dataset{aestheticskg2025,
  title     = {Aesthetics-KG: A Knowledge Graph of Internet Aesthetics},
  author    = {Cappa, Silvia and Lippolis, Anna Sofia and Flinkert, Anouk and
               Krasnova, Ekaterina and Nakamura, Shiho and
               Nuzzolese, Andrea Giovanni and Gangemi, Aldo},
  year      = {2025},
  doi       = {10.5281/zenodo.20039664},
  url       = {https://doi.org/10.5281/zenodo.20039664},
  publisher = {Zenodo}
}
```

---

## License

| Component | License |
|---|---|
| Code (`code/`) | [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) |
| Graph data & evaluation | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) (inherits from Aesthetics Wiki) |

---

## Contributors

Silvia Cappa · Anna Sofia Lippolis · Anouk Flinkert · Ekaterina Krasnova · Shiho Nakamura · Andrea Giovanni Nuzzolese · Aldo Gangemi

CNR-ISTC · University of Bologna (DH.arc)
