# User Story: Digital Humanities Researcher

### 1. Persona
**Name:** Lily  
**Role:** Digital Humanities Researcher   
**Description:** Lily studies how cultural forms and aesthetic sensibilities migrate across different media, platforms and historical periods.

### 2. Scenario & Motivation
As a scholar, Lily is building a comparative corpus of aesthetic movements. She is interested in the **transmediality** of aesthetics—how a single "vibe" or sensibility (like *Dark Academia* or *Cyberpunk*) manifests simultaneously in diverse domains such as film, literature, music, and architecture. 

Rather than treating aesthetics as mere visual labels, Lily uses **AestheticsKG** to trace their symbolic and cross-domain dimensions. This allows her to move beyond "algorithmic bubbles" and see how an aesthetic is rooted in specific geographic locations or historical contexts.

### 3. Competency Questions & SPARQL Implementation
Lily uses the ontology to answer the following research questions:

1. **CQ1:** Which artworks (films, music, literature) are associated with a given aesthetic?
```sparql
SELECT ?workTitle ?workType
WHERE {
  ?aesthetic a ae-ont:Aesthetic ;
             ae-ont:name ?aestheticName ;
             ae-ont:hasRelatedWork ?work .
  ?work a ?workType ;
        rdfs:label ?workTitle .
  FILTER(str(?aestheticName) = "Dark Academia")
  FILTER(?workType != owl:NamedIndividual)
}
ORDER BY ?workType ?workTitle
```
2. **CQ2:** Which aesthetics are associated with works of a specific medium (e.g., Film)?
```sparql
SELECT ?aestheticName (COUNT(?work) AS ?filmCount)
WHERE {
  ?aesthetic a ae-ont:Aesthetic ;
             ae-ont:name ?aestheticName ;
             ae-ont:hasRelatedWork ?work .
  ?work a ae-ont:Film .
}
GROUP BY ?aestheticName
ORDER BY DESC(?filmCount)
LIMIT 20
```
3. **CQ3:** Which aesthetics are linked to a specific geographic location of origin?
```sparql
SELECT ?aestheticName ?locationLabel
WHERE {
  ?aesthetic a ae-ont:Aesthetic ;
             ae-ont:name ?aestheticName ;
             ae-ont:hasLocationOfOrigin ?location .
  ?location rdfs:label ?locationLabel .
  FILTER(CONTAINS(LCASE(str(?locationLabel)), "japan"))
}
ORDER BY ?aestheticName
```

