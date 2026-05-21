# User Story: Recommender System Developer

### 1. Persona
**Name:** Alex  
**Role:** Backend developer  
**Description:** Alex is building a recommendation engine for a creative e-commerce platform. His task is to surface products and content that match the complex, often "vague" aesthetic preferences of users.

### 2. Scenario & Motivation
Modern e-commerce requires more than just keyword matching; it needs "vibe-matching". If a user likes *Dark Academia*, they might also enjoy *Light Academia* or *Gothic Revival*, but a simple search won't always connect these dots.

Alex uses **AestheticsKG** as a knowledge graph to power his recommendation logic. By traversing the relationships in the graph (like subgenres, influences, and shared values), his system can calculate "aesthetic proximity." This allows the platform to suggest products that are stylistically relevant, even if they belong to different categories.

### 3. Competency Questions & SPARQL Implementation
Alex uses these queries to build his recommendation clusters:

1. **CQ1:** Which aesthetics are subgenres of a given aesthetic?
```sparql
SELECT ?subgenreName
WHERE {
  ?aesthetic a vibe:Aesthetic ;
             vibe:name ?aestheticName ;
             vibe:hasSubgenre ?sub .
  ?sub vibe:name ?subgenreName .
  FILTER(str(?aestheticName) = "Punk")
}
ORDER BY ?subgenreName
```
2. **CQ2:** Which aesthetics have influenced a given aesthetic?
```sparql
SELECT ?influencerName
WHERE {
  ?aesthetic a vibe:Aesthetic ;
             vibe:name ?n .
  FILTER(str(?n) = "DIY Punk")
  ?aesthetic vibe:follows ?influencer .
  ?influencer vibe:name ?influencerName .
}
```
3. **CQ3:** Which aesthetics are related to a given one and share at least one value?
```sparql
SELECT DISTINCT ?relatedName ?relationType WHERE {
  ?source a vibe:Aesthetic ; vibe:name ?sourceName .
  FILTER(str(?sourceName) = "Memphis Lite")
  { ?source vibe:hasSubgenre ?related . BIND("subgenre" AS ?relationType) }
  UNION { ?source vibe:follows ?related . BIND("follows" AS ?relationType) }
  UNION { ?source vibe:precedes ?related . BIND("precedes" AS ?relationType) }
  UNION { ?source vibe:relatedTo ?related . BIND("relatedTo" AS ?relationType) }
  ?related vibe:name ?relatedName .
} ORDER BY ?relationType
```
