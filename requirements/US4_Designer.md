# User Story: Designer & Branding specialist

### 1. Persona
**Name:** Matteo  
**Role:** Visual Designer / Brand Manager   
**Description:** Matteo works with fashion brands and creative studios. He uses aesthetic research to create moodboards, brand guidelines, and new collection concepts.

### 2. Scenario & Motivation
When working on a new visual identity, Matteo needs to quickly grasp the defining visual and material characteristics of an aesthetic. Whether he wants to follow the conventions of a style (like *Frutiger Aero*) or deliberately subvert them (e.g., creating a "Dark" version of a typically bright aesthetic), he needs structured data.

**AestheticsKG** allows Matteo to retrieve recurring **motifs**, **color palettes**, and **brand associations** without spending hours on Pinterest. This structured approach helps him identify "visual DNA" and discover related styles that might share similar stylistic roots.

### 3. Competency Questions & SPARQL Implementation
Matteo uses the ontology to find answer to these questions:

1. **CQ1:** Which aesthetics share a given color palette entry?
```sparql
SELECT ?aestheticName
WHERE {
  ?aesthetic a vibe:Aesthetic ;
             vibe:name ?aestheticName ;
             vibe:hasMember ?color .
  ?color a vibe:Color ;
         rdfs:label "black"@en .
}
ORDER BY ?aestheticName
LIMIT 30
```
2. **CQ2:** Which motifs are characteristic of a particular aesthetic?
```sparql
SELECT ?motifLabel
WHERE {
  ?aesthetic a vibe:Aesthetic ;
             vibe:name ?aestheticName ;
             vibe:hasMember ?motif .
  ?motif a vibe:Motif ;
         rdfs:label ?motifLabel .
  FILTER(str(?aestheticName) = "Gothic")
}
ORDER BY ?motifLabel
```
3. **CQ3:** Which brands are associated with a given aesthetic?
```sparql
SELECT ?brandLabel
WHERE {
  ?aesthetic a vibe:Aesthetic ;
             vibe:name ?aestheticName ;
             vibe:hasRelatedBrand ?brand .
  ?brand rdfs:label ?brandLabel .
  FILTER(str(?aestheticName) = "Preppy")
}
ORDER BY ?brandLabel
```
4. **CQ4:** Which aesthetics are visually or stylistically related to a given one?
```sparql
SELECT ?relatedName ?relationType WHERE {
  ?aesthetic a vibe:Aesthetic ; vibe:name ?aestheticName .
  FILTER(str(?aestheticName) = "Cottagecore")
  { ?aesthetic vibe:relatedTo ?related . BIND("relatedTo" AS ?relationType) }
  UNION { ?aesthetic vibe:hasSubgenre ?related . BIND("hasSubgenre" AS ?relationType) }
  UNION { ?aesthetic vibe:follows ?related . BIND("follows" AS ?relationType) }
  UNION { ?aesthetic vibe:precedes ?related . BIND("precedes" AS ?relationType) }
  ?related vibe:name ?relatedName .
} ORDER BY ?relationType ?relatedName
```
