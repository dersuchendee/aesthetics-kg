#!/usr/bin/env python3
"""
rag_eval.py
ANSWER1 = Baseline LLM — Gemini answering from general knowledge only (no graph)
ANSWER2 = RAG-enriched  — primary SPARQL + supplementary retrieval → Gemini produces
          a rich descriptive narrative grounded entirely in the KG data

Row 2 of the CSV contains dimension definitions for annotators.
"""

import csv, time, textwrap
import requests

ENDPOINT   = "https://semantics.istc.cnr.it/aesthetics-kg/graphdb/repositories/aesthetics"
GEMINI_KEY = "AIzaSyAZDGa3nhdCk8U-8KG9SCsRax-zq72XW7Q"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
)

# ---------------------------------------------------------------------------
# CQ definitions  (sparql = primary query; extra_sparql = supplementary enrichment)
# ---------------------------------------------------------------------------
CQS = [
    {
        "id": "U1-CQ1", "user": "User 1",
        "question": "What is the primary geographical and/or platform area of distribution for Cottagecore?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?locationLabel ?platformLabel WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Cottagecore"@en .
  OPTIONAL { ?a ae-ont:hasLocationOfOrigin ?l . ?l rdfs:label ?locationLabel . }
  OPTIONAL { ?a ae-ont:hasPrimaryPlatform ?p . ?p rdfs:label ?platformLabel . }
}""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
SELECT ?def ?period WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Cottagecore"@en .
  OPTIONAL { ?a skos:definition ?def . }
  OPTIONAL { ?a ae-ont:hasOriginPeriod ?p . ?p ae-ont:approximateLabel ?period . }
} LIMIT 3""",
    },
    {
        "id": "U1-CQ2", "user": "User 1",
        "question": "Which aesthetics originated in 2000 or later, reflecting the digital turn in aesthetic creation? Give the first 20 by start year.",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?aestheticName ?startYear WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name ?aestheticName ;
     ae-ont:hasOriginPeriod ?p . ?p ae-ont:startYear ?startYear .
  FILTER(?startYear >= "2000"^^xsd:gYear)
} ORDER BY ?startYear LIMIT 20""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?name ?platformLabel WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name ?name ;
     ae-ont:hasOriginPeriod ?p ; ae-ont:hasPrimaryPlatform ?pl .
  ?p ae-ont:startYear ?sy . ?pl rdfs:label ?platformLabel .
  FILTER(?sy >= "2010"^^<http://www.w3.org/2001/XMLSchema#gYear>)
} LIMIT 10""",
    },
    {
        "id": "U2-CQ1", "user": "User 2",
        "question": "Which artworks (films, music, literature, anime) are associated with Dark Academia?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:    <http://www.w3.org/2002/07/owl#>
SELECT ?workTitle ?workType WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Dark Academia"@en ;
     ae-ont:hasRelatedWork ?w .
  ?w a ?workType ; rdfs:label ?workTitle .
  FILTER(?workType != owl:NamedIndividual)
} ORDER BY ?workType ?workTitle LIMIT 30""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?def ?locationLabel WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Dark Academia"@en .
  OPTIONAL { ?a skos:definition ?def . }
  OPTIONAL { ?a ae-ont:hasLocationOfOrigin ?l . ?l rdfs:label ?locationLabel . }
} LIMIT 3""",
    },
    {
        "id": "U2-CQ2", "user": "User 2",
        "question": "Which aesthetics are most associated with films? List the top 10 by number of associated films.",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
SELECT ?aestheticName (COUNT(?w) AS ?filmCount) WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name ?aestheticName ;
     ae-ont:hasRelatedWork ?w .
  ?w a ae-ont:Film .
} GROUP BY ?aestheticName ORDER BY DESC(?filmCount) LIMIT 10""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?film WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Catholic Horror"@en ;
     ae-ont:hasRelatedWork ?w .
  ?w a ae-ont:Film ; rdfs:label ?film .
} LIMIT 8""",
    },
    {
        "id": "U2-CQ3", "user": "User 2",
        "question": "Which aesthetics are linked to Japan as a geographic location of origin?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?aestheticName ?locationLabel WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name ?aestheticName ;
     ae-ont:hasLocationOfOrigin ?l .
  ?l rdfs:label ?locationLabel .
  FILTER(CONTAINS(LCASE(str(?locationLabel)), "japan"))
} ORDER BY ?aestheticName LIMIT 30""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?name ?period WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name ?name ;
     ae-ont:hasLocationOfOrigin ?l ; ae-ont:hasOriginPeriod ?p .
  ?l rdfs:label ?ll . ?p ae-ont:approximateLabel ?period .
  FILTER(CONTAINS(LCASE(str(?ll)), "japan"))
} LIMIT 10""",
    },
    {
        "id": "U3-CQ2", "user": "User 3",
        "question": "Which aesthetics are associated with TikTok as a platform, and what brands are present there?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?aestheticName ?brandLabel WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name ?aestheticName ;
     ae-ont:hasPrimaryPlatform ?p ; ae-ont:hasRelatedBrand ?b .
  ?p rdfs:label ?platformLabel . ?b rdfs:label ?brandLabel .
  FILTER(CONTAINS(LCASE(str(?platformLabel)), "tiktok"))
} ORDER BY ?aestheticName LIMIT 30""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?name (COUNT(DISTINCT ?b) AS ?brandCount) WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name ?name ;
     ae-ont:hasPrimaryPlatform ?p ; ae-ont:hasRelatedBrand ?b .
  ?p rdfs:label ?pl . FILTER(CONTAINS(LCASE(str(?pl)), "tiktok"))
} GROUP BY ?name ORDER BY DESC(?brandCount) LIMIT 10""",
    },
    {
        "id": "U3-CQ4", "user": "User 3",
        "question": "Which brands are representative associations of Normcore?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?brandLabel WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Normcore"@en ;
     ae-ont:hasRelatedBrand ?b .
  ?b rdfs:label ?brandLabel .
} ORDER BY ?brandLabel""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
SELECT ?def ?valueLabel WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Normcore"@en .
  OPTIONAL { ?a skos:definition ?def . }
  OPTIONAL { ?a ae-ont:hasMember ?v . ?v a ae-ont:Value ; rdfs:label ?valueLabel . }
} LIMIT 10""",
    },
    {
        "id": "U4-CQ1", "user": "User 4",
        "question": "Which aesthetics share black as a key color palette entry?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?aestheticName WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name ?aestheticName ;
     ae-ont:hasMember ?c .
  ?c a ae-ont:Color ; rdfs:label "black"@en .
} ORDER BY ?aestheticName LIMIT 30""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?name ?otherColor WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name ?name ;
     ae-ont:hasMember ?c1 ; ae-ont:hasMember ?c2 .
  ?c1 a ae-ont:Color ; rdfs:label "black"@en .
  ?c2 a ae-ont:Color ; rdfs:label ?otherColor .
  FILTER(str(?otherColor) != "black")
} LIMIT 15""",
    },
    {
        "id": "U4-CQ2", "user": "User 4",
        "question": "Which motifs are characteristic of Gothic?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?motifLabel WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Gothic"@en ;
     ae-ont:hasMember ?m .
  ?m a ae-ont:Motif ; rdfs:label ?motifLabel .
} ORDER BY ?motifLabel""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
SELECT ?def ?valueLabel ?colorLabel WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Gothic"@en .
  OPTIONAL { ?a skos:definition ?def . }
  OPTIONAL { ?a ae-ont:hasMember ?v . ?v a ae-ont:Value ; rdfs:label ?valueLabel . }
  OPTIONAL { ?a ae-ont:hasMember ?c . ?c a ae-ont:Color ; rdfs:label ?colorLabel . }
} LIMIT 10""",
    },
    {
        "id": "U4-CQ3", "user": "User 4",
        "question": "Which brands are associated with Preppy?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?brandLabel WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Preppy"@en ;
     ae-ont:hasRelatedBrand ?b .
  ?b rdfs:label ?brandLabel .
} ORDER BY ?brandLabel""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?motifLabel ?valueLabel WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Preppy"@en .
  OPTIONAL { ?a ae-ont:hasMember ?m . ?m a ae-ont:Motif ; rdfs:label ?motifLabel . }
  OPTIONAL { ?a ae-ont:hasMember ?v . ?v a ae-ont:Value ; rdfs:label ?valueLabel . }
} LIMIT 10""",
    },
    {
        "id": "U4-CQ4", "user": "User 4",
        "question": "Which aesthetics are visually or stylistically related to Cottagecore?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
SELECT ?relatedName ?relationType WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Cottagecore"@en .
  { ?a ae-ont:relatedTo ?r . BIND("relatedTo" AS ?relationType) }
  UNION { ?a ae-ont:hasSubgenre ?r . BIND("hasSubgenre" AS ?relationType) }
  UNION { ?a ae-ont:follows ?r . BIND("follows" AS ?relationType) }
  UNION { ?a ae-ont:precedes ?r . BIND("precedes" AS ?relationType) }
  ?r ae-ont:name ?relatedName .
} ORDER BY ?relationType ?relatedName""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
SELECT ?def ?period WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Cottagecore"@en .
  OPTIONAL { ?a skos:definition ?def . }
  OPTIONAL { ?a ae-ont:hasOriginPeriod ?p . ?p ae-ont:approximateLabel ?period . }
} LIMIT 3""",
    },
    {
        "id": "U5-CQ1", "user": "User 5",
        "question": "Which aesthetics are subgenres of Punk?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
SELECT ?subgenreName WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Punk"@en ;
     ae-ont:hasSubgenre ?s .
  ?s ae-ont:name ?subgenreName .
} ORDER BY ?subgenreName""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?name ?locationLabel WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Punk"@en ;
     ae-ont:hasSubgenre ?s .
  ?s ae-ont:name ?name .
  OPTIONAL { ?s ae-ont:hasLocationOfOrigin ?l . ?l rdfs:label ?locationLabel . }
} LIMIT 10""",
    },
    {
        "id": "U5-CQ2", "user": "User 5",
        "question": "Which aesthetics influenced DIY Punk, and which aesthetics did it in turn influence?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
SELECT ?name ?relation WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "DIY Punk"@en .
  { ?a ae-ont:follows ?r . ?r ae-ont:name ?name . BIND("follows (was influenced by)" AS ?relation) }
  UNION { ?a ae-ont:precedes ?r . ?r ae-ont:name ?name . BIND("precedes (later influenced)" AS ?relation) }
}""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?def ?motif ?value WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "DIY Punk"@en .
  OPTIONAL { ?a skos:definition ?def . }
  OPTIONAL { ?a ae-ont:hasMember ?m . ?m a ae-ont:Motif ; rdfs:label ?motif . }
  OPTIONAL { ?a ae-ont:hasMember ?v . ?v a ae-ont:Value ; rdfs:label ?value . }
} LIMIT 8""",
    },
    {
        "id": "U6-CQ1", "user": "User 6",
        "question": "Which aesthetics have the highest number of sub-aesthetics or derivative movements?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
SELECT ?aestheticName (COUNT(?s) AS ?subCount) WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name ?aestheticName ;
     ae-ont:hasSubgenre ?s .
} GROUP BY ?aestheticName ORDER BY DESC(?subCount) LIMIT 10""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
SELECT ?sub WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Punk"@en ; ae-ont:hasSubgenre ?s .
  ?s ae-ont:name ?sub .
} LIMIT 16""",
    },
    {
        "id": "U6-CQ2", "user": "User 6",
        "question": "Which aesthetics have the longest chain of cultural influence (precedes+)?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
SELECT ?aestheticName (COUNT(DISTINCT ?d) AS ?chainLength) WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name ?aestheticName .
  ?a ae-ont:precedes+ ?d .
} GROUP BY ?aestheticName ORDER BY DESC(?chainLength) LIMIT 10""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
SELECT ?descendant WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Italian Renaissance"@en .
  ?a ae-ont:precedes+ ?d . ?d ae-ont:name ?descendant .
} LIMIT 10""",
    },
    {
        "id": "U6-CQ3", "user": "User 6",
        "question": "Which aesthetics share fashion-related motifs (dresses, jackets, boots, skirts, jeans, clothing) as defining elements?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?aestheticName ?motifLabel WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name ?aestheticName ; ae-ont:hasMember ?m .
  ?m a ae-ont:Motif ; rdfs:label ?motifLabel .
  FILTER(CONTAINS(LCASE(str(?motifLabel)),"dress") || CONTAINS(LCASE(str(?motifLabel)),"jacket") ||
         CONTAINS(LCASE(str(?motifLabel)),"boots") || CONTAINS(LCASE(str(?motifLabel)),"skirt")  ||
         CONTAINS(LCASE(str(?motifLabel)),"jeans") || CONTAINS(LCASE(str(?motifLabel)),"clothing"))
} ORDER BY ?aestheticName LIMIT 30""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
SELECT (COUNT(DISTINCT ?a) AS ?aestheticsWithFashionMotifs) WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:hasMember ?m . ?m a ae-ont:Motif ; rdfs:label ?lbl .
  FILTER(CONTAINS(LCASE(str(?lbl)),"dress") || CONTAINS(LCASE(str(?lbl)),"jacket") ||
         CONTAINS(LCASE(str(?lbl)),"boots") || CONTAINS(LCASE(str(?lbl)),"skirt")  ||
         CONTAINS(LCASE(str(?lbl)),"jeans") || CONTAINS(LCASE(str(?lbl)),"clothing"))
}""",
    },
    {
        "id": "U6-CQ4", "user": "User 6",
        "question": "Which aesthetic has the highest number of associated brands?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
SELECT ?aestheticName (COUNT(DISTINCT ?b) AS ?brandCount) WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name ?aestheticName ;
     ae-ont:hasRelatedBrand ?b .
} GROUP BY ?aestheticName ORDER BY DESC(?brandCount) LIMIT 10""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?brand WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name "Hip-Hop"@en ;
     ae-ont:hasRelatedBrand ?b . ?b rdfs:label ?brand .
} LIMIT 10""",
    },
    {
        "id": "U7-CQ1", "user": "User 7",
        "question": "Which aesthetics from the 2000s–2010s have contemporary revivals or derivative movements?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?originalName ?revivalName WHERE {
  ?original a ae-ont:Aesthetic ; ae-ont:name ?originalName ;
            ae-ont:hasOriginPeriod ?op . ?op ae-ont:startYear ?sy .
  ?revival  a ae-ont:Aesthetic ; ae-ont:name ?revivalName ;
            ae-ont:follows ?original ;
            ae-ont:hasOriginPeriod ?rp . ?rp ae-ont:startYear ?ry .
  FILTER(?ry > ?sy)
} ORDER BY ?originalName LIMIT 30""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?revivalName ?platform WHERE {
  ?original a ae-ont:Aesthetic ; ae-ont:name "Grunge"@en .
  ?revival a ae-ont:Aesthetic ; ae-ont:follows ?original ; ae-ont:name ?revivalName .
  OPTIONAL { ?revival ae-ont:hasPrimaryPlatform ?p . ?p rdfs:label ?platform . }
} LIMIT 5""",
    },
    {
        "id": "U7-CQ2", "user": "User 7",
        "question": "Which aesthetics are associated with nostalgia as a core value?",
        "sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?aestheticName WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name ?aestheticName ;
     ae-ont:hasMember ?v . ?v rdfs:label ?lbl .
  FILTER(CONTAINS(LCASE(str(?lbl)), "nostalg"))
} ORDER BY ?aestheticName LIMIT 30""",
        "extra_sparql": """
PREFIX ae-ont: <https://w3id.org/aesthetics-kg/ontology/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?name ?period WHERE {
  ?a a ae-ont:Aesthetic ; ae-ont:name ?name ;
     ae-ont:hasMember ?v ; ae-ont:hasOriginPeriod ?p .
  ?v rdfs:label ?lbl . ?p ae-ont:approximateLabel ?period .
  FILTER(CONTAINS(LCASE(str(?lbl)), "nostalg"))
} LIMIT 10""",
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sparql_query(query: str) -> list[dict]:
    resp = requests.get(
        ENDPOINT,
        params={"query": query.strip()},
        headers={"Accept": "application/sparql-results+json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["results"]["bindings"]

def rows_to_text(bindings: list[dict], label: str = "") -> str:
    if not bindings:
        return f"{label}(no results)"
    vars_ = list(bindings[0].keys())
    lines = [f"{label}" + " | ".join(vars_)]
    for b in bindings:
        lines.append("  " + " | ".join(b.get(v, {}).get("value", "—") for v in vars_))
    return "\n".join(lines)

def gemini(prompt: str) -> str:
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = requests.post(GEMINI_URL, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

# ANSWER1 — baseline LLM, no graph
LLM_PROMPT = textwrap.dedent("""\
    You are an expert on internet aesthetics, subcultures, and visual culture.
    Answer the following question based on your general knowledge.
    Be informative and descriptive (4–7 sentences). Do not use bullet lists.

    Question: {question}
""")

# ANSWER2 — RAG enriched: primary data + supplementary context
RAG_PROMPT = textwrap.dedent("""\
    You are an expert on internet aesthetics, subcultures, and visual culture.
    You have been given structured data retrieved from a Knowledge Graph (KG) about aesthetics.
    Using the KG data as your primary source, write a rich, descriptive answer to the question.
    Mention specific names, counts, and relationships from the data.
    You may add brief contextual explanation to make the answer self-contained,
    but do not invent facts not supported by the data provided.
    Write in flowing prose (4–8 sentences), no bullet lists.

    --- PRIMARY KG DATA ---
    {primary}

    --- SUPPLEMENTARY KG DATA ---
    {supplementary}

    Question: {question}
""")

# ---------------------------------------------------------------------------
# Definitions row (row 2 in the CSV)
# ---------------------------------------------------------------------------
DEFINITIONS = {
    "cq_id":                      "Competency Question identifier",
    "user":                       "Evaluator who authored the CQ",
    "question":                   "Natural language competency question",
    "kg_context":                 "Raw SPARQL results used as KG context (primary + supplementary)",
    "ANSWER1":                    "Baseline LLM answer — Gemini with NO graph context (general knowledge only)",
    "ANSWER2":                    "RAG-enriched answer — Gemini grounded in KG data + supplementary retrieval",
    "completeness_ANSWER1":       "1–5: Does ANSWER1 cover all aspects the question asks for?",
    "accuracy_ANSWER1":           "1–5: Is the information in ANSWER1 factually correct?",
    "self_containedness_ANSWER1": "1–5: Can ANSWER1 be understood without external lookup?",
    "fitness_ANSWER1":            "1–5: Is ANSWER1 directly responsive to the question in the right form?",
    "completeness_ANSWER2":       "1–5: Does ANSWER2 cover all aspects the question asks for?",
    "accuracy_ANSWER2":           "1–5: Is the information in ANSWER2 factually correct?",
    "self_containedness_ANSWER2": "1–5: Can ANSWER2 be understood without external lookup?",
    "fitness_ANSWER2":            "1–5: Is ANSWER2 directly responsive to the question in the right form?",
    "notes":                      "Free-text annotations",
}

HEADER = list(DEFINITIONS.keys())

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
OUT = "/Users/annasofialippolis/aestheticswork/rag_eval.csv"

rows = [DEFINITIONS]  # row 2 = definitions

for i, cq in enumerate(CQS):
    print(f"[{i+1}/{len(CQS)}] {cq['id']} — querying KG…")

    try:
        primary   = sparql_query(cq["sparql"])
        primary_t = rows_to_text(primary, "PRIMARY:\n")
    except Exception as e:
        primary_t = f"(SPARQL error: {e})"

    try:
        extra   = sparql_query(cq["extra_sparql"])
        extra_t = rows_to_text(extra, "SUPPLEMENTARY:\n")
    except Exception as e:
        extra_t = f"(extra SPARQL error: {e})"

    kg_ctx = primary_t + "\n\n" + extra_t

    print(f"         generating ANSWER1 (LLM baseline)…")
    try:
        a1 = gemini(LLM_PROMPT.format(question=cq["question"]))
    except Exception as e:
        a1 = f"(Gemini error: {e})"

    print(f"         generating ANSWER2 (RAG enriched)…")
    try:
        a2 = gemini(RAG_PROMPT.format(
            question=cq["question"],
            primary=primary_t,
            supplementary=extra_t,
        ))
    except Exception as e:
        a2 = f"(Gemini error: {e})"

    rows.append({
        "cq_id": cq["id"],
        "user":  cq["user"],
        "question": cq["question"],
        "kg_context": kg_ctx,
        "ANSWER1": a1,
        "ANSWER2": a2,
        **{c: "" for c in HEADER if c not in ("cq_id","user","question","kg_context","ANSWER1","ANSWER2")},
    })

    time.sleep(1)

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=HEADER)
    w.writeheader()
    w.writerows(rows)

print(f"\nDone. {len(rows)-1} CQs → {OUT}")
