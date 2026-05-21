#!/usr/bin/env python3
"""
run_rml.py
Executes the RML mapping (mapping.rml.ttl) using pyrml-lib and serialises
the resulting RDF graph to Turtle, RDF/XML, and JSON-LD.

Run from inside aestheticswork/:
    python3 run_rml.py
"""

import logging
import os
import time
import numpy as np
from pathlib import Path
from rdflib import URIRef, Namespace
from rdflib.namespace import RDF, RDFS, OWL, SKOS, XSD

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

BASE    = Path(__file__).parent
MAPPING = BASE / "mapping.rml.ttl"
OUT_TTL = BASE / "aestheticskg_rml.ttl"
OUT_XML = BASE / "aestheticskg_rml.rdf"
OUT_JLD = BASE / "aestheticskg_rml.jsonld"

# pyrml resolves relative paths from the current working directory
os.chdir(BASE)

log.info("Loading pyrml mapper…")
from pyrml import PyRML
import pyrml.pyrml_core as pyrml_core

# --- Patch pyrml bug: ConstantPredicate caches results keyed by the predicate
# URI itself, so all TriplesMaps that use e.g. rdfs:label share one cached
# row-count from the first evaluation.  Bypass the cache for constant predicates
# so each call re-creates the array for the actual data source row count. ---
def _cp_apply_nocache(self, data_source):
    n_rows = data_source.data.shape[0]
    return np.array(
        [URIRef(self._constant) if self._constant else None for _ in range(n_rows)],
        dtype=URIRef,
    )

pyrml_core.ConstantPredicate.apply = _cp_apply_nocache

mapper = PyRML.get_mapper()

log.info(f"Running mapping: {MAPPING.name}")
t0 = time.time()
g = mapper.convert(str(MAPPING))
elapsed = time.time() - t0

log.info(f"Mapping done in {elapsed:.1f}s — {len(g):,} triples")

# Bind readable namespace prefixes so the output uses ae-ont:/vibe: not ns1:/ns2:
g.bind("ae-ont",   Namespace("https://w3id.org/aesthetics-kg/ontology/"))
g.bind("vibe",     Namespace("https://w3id.org/vibe-ontology/"))
g.bind("ae-res",   Namespace("https://w3id.org/aesthetics-kg/resource/"))
g.bind("skos",     SKOS)
g.bind("owl",      OWL)
g.bind("rdfs",     RDFS)
g.bind("xsd",      XSD)

log.info(f"Serialising → {OUT_TTL.name}")
g.serialize(destination=str(OUT_TTL), format="turtle")
log.info(f"  {OUT_TTL.stat().st_size / 1e6:.1f} MB")

log.info(f"Serialising → {OUT_XML.name}")
g.serialize(destination=str(OUT_XML), format="xml")
log.info(f"  {OUT_XML.stat().st_size / 1e6:.1f} MB")

log.info(f"Serialising → {OUT_JLD.name}")
g.serialize(destination=str(OUT_JLD), format="json-ld")
log.info(f"  {OUT_JLD.stat().st_size / 1e6:.1f} MB")

log.info("\nDone.")
