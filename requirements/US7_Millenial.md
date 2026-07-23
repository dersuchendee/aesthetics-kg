# User Story: Millennial User 

### 1. Persona
**Name:** Marco  
**Age:** 34  
**Role:** Millennial Content Creator   
**Description:** Marco grew up during the era of Tumblr, early YouTube and MySpace. For him, aesthetics are deeply tied to personal memory, nostalgia and an evolution of the web.

### 2. Scenario & Motivation
Marco often tries to articulate why certain visual styles feel like "his era". He wants to understand the visual logic of the early 2000s and the emotional registers of movements like *Emo* or *Scene*. 

Using **AestheticsKG**, Marco explores the genealogy of the aesthetics he lived through. He wants to see which of them have been revived (like *Y2K*), which ones gave rise to current TikTok micro-trends, and how brands have reappropriated the subcultures of his youth for modern marketing. It’s an exploration of cultural identity through data.

### 3. Competency Questions & SPARQL Implementation
Marco uses the ontology to investigate more about his interest:

1. **CQ1:** Which aesthetics originated in the 2000s–2010s and have contemporary revivals or derivatives?
```sparql
SELECT DISTINCT ?originalName ?revivalName WHERE {
  ?original a vibe:Aesthetic ; 
            vibe:name ?originalName ;
            vibe:hasOriginPeriod ?op . 
  ?op       vibe:startYear ?sy .
  
  ?revival  a vibe:Aesthetic ; 
            vibe:name ?revivalName ;
            vibe:follows ?original ;
            vibe:hasOriginPeriod ?rp . 
  ?rp       vibe:startYear ?ry .
  
  FILTER(?ry > ?sy)
} 
ORDER BY ?originalName 
LIMIT 30

```
2. **CQ2:** Which aesthetics are associated with nostalgia?
```sparql
SELECT ?name ?valueLabel
WHERE {
  ?aesthetic a vibe:Aesthetic ;
             vibe:name ?name ;
             vibe:hasMember ?value .
  ?value rdfs:label ?valueLabel .
  FILTER(CONTAINS(LCASE(str(?valueLabel)), "nostalgia"))
}
ORDER BY ?name
```
3. **CQ3:** Which brands are associated with aesthetics that have subgenres or revivals?
```sparql
SELECT DISTINCT ?name ?brandLabel ?subgenreName
WHERE {
  ?aesthetic a vibe:Aesthetic ;
             vibe:name ?name ;
             vibe:hasSubgenre ?sub ;
             vibe:hasRelatedBrand ?brand .
  ?sub vibe:name ?subgenreName .
  ?brand rdfs:label ?brandLabel .
}
ORDER BY ?name
```
