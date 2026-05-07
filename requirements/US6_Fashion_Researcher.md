# User Story: Fashion Researcher & Trend Analyst

### 1. Persona
**Name:** Camille  
**Role:** Fashion Researcher / Trend Analyst  
**Description:** Camille studies the generative genealogy of aesthetic movements. She focuses on identifying which "parent" aesthetics have been the most culturally fertile, giving rise to derivative styles and sub-movements.

### 2. Scenario & Motivation
Camille is interested in mapping "aesthetic family trees." For her, an aesthetic isn't a static category but a living lineage. She investigates how *Y2K* spawned *Bimbocore*, how *Fairycore* influenced *Goblincore*, or how *Punk* fragmented into dozens of sub-genres over decades.

By using **AestheticsKG**, Camille can move beyond anecdotal evidence. She uses the graph to calculate the "generative power" of a movement based on its number of descendants and the length of its influence chains. This allows her to identify which aesthetics are "core nodes" in the history of digital and physical fashion.

### 3. Competency Questions & SPARQL Implementation

1. **CQ1:** Which aesthetics have the highest number of sub-aesthetics or derivative movements?
```sparql
SELECT ?aestheticName (COUNT(?sub) AS ?subCount)
WHERE {
  ?aesthetic a ae-ont:Aesthetic ;
             ae-ont:name ?aestheticName ;
             ae-ont:hasSubgenre ?sub .
}
GROUP BY ?aestheticName
ORDER BY DESC(?subCount)
LIMIT 20
```
2. **CQ2:** Which aesthetics have the longest chain of influence (transitive influence)?
```sparql
SELECT ?aestheticName (COUNT(DISTINCT ?descendant) AS ?chainLength)
WHERE {
  ?aesthetic a ae-ont:Aesthetic ;
             ae-ont:name ?aestheticName .
  ?aesthetic ae-ont:precedes+ ?descendant .
}
GROUP BY ?aestheticName
ORDER BY DESC(?chainLength)
LIMIT 10
```
3. **CQ3:** Which aesthetics share fashion-related motifs as defining elements?
```sparql
SELECT DISTINCT ?aestheticName ?motifLabel
WHERE {
  ?aesthetic a ae-ont:Aesthetic ;
             ae-ont:name ?aestheticName ;
             ae-ont:hasMember ?motif .
  ?motif a ae-ont:Motif ;
         rdfs:label ?motifLabel .
  FILTER(
    CONTAINS(LCASE(str(?motifLabel)), "dress")  ||
    CONTAINS(LCASE(str(?motifLabel)), "clothing") ||
    CONTAINS(LCASE(str(?motifLabel)), "outfit")  ||
    CONTAINS(LCASE(str(?motifLabel)), "jacket")  ||
    CONTAINS(LCASE(str(?motifLabel)), "boots")   ||
    CONTAINS(LCASE(str(?motifLabel)), "skirt")   ||
    CONTAINS(LCASE(str(?motifLabel)), "jeans")
  )
}
ORDER BY ?aestheticName
LIMIT 40
```
4. **CQ4:** Which aesthetic has the highest number of associated brands?
```sparql
SELECT ?aestheticName (COUNT(DISTINCT ?brand) AS ?brandCount)
WHERE {
  ?aesthetic a ae-ont:Aesthetic ;
             ae-ont:name ?aestheticName ;
             ae-ont:hasRelatedBrand ?brand .
}
GROUP BY ?aestheticName
ORDER BY DESC(?brandCount)
LIMIT 20
```
