# User Story: Social & Cultural Anthropologist

### 1. Persona
**Name:** David  
**Role:** Social & Cultural Anthropologist  
**Description:** David studies digital communities and how aesthetics function as a form of social identity.  

### 2. Scenario & Motivation
Anthropologists studying digital environments face a methodological challenge: recommendation algorithms (like TikTok's FYP) create "filter bubbles." This makes it hard for a researcher to see a representative "cross-section" of an aesthetic beyond their own algorithmic feed. 

**AestheticsKG** serves as a counterbalance to this bias. It provides David with a systematic, community-grounded map of aesthetic categories that is independent of individual algorithmic tailoring.

### 3. Competency Questions & SPARQL implementation
These are the questions David can answer using the AestheticsKG:
1. **CQ1:** What is the primary geographical and/or platform area of distribution for a given aesthetic?
```sparql
PREFIX ae-ont: [https://w3id.org/aesthetics-kg/ontology/](https://w3id.org/aesthetics-kg/ontology/)
PREFIX rdfs: [http://www.w3.org/2000/01/rdf-schema#](http://www.w3.org/2000/01/rdf-schema#)

SELECT ?aestheticName ?locationLabel ?platformLabel
WHERE {
  ?aesthetic a ae-ont:Aesthetic ;
             ae-ont:name ?aestheticName .
  OPTIONAL {
    ?aesthetic ae-ont:hasLocationOfOrigin ?location .
    ?location rdfs:label ?locationLabel .
  }
  OPTIONAL {
    ?aesthetic ae-ont:hasPrimaryPlatform ?platform .
    ?platform rdfs:label ?platformLabel .
  }
  FILTER(str(?aestheticName) = "Cottagecore")
}
```
2. **CQ2:** During which time period did the digital turn in aesthetics creation occur? (aesthetics with origin period 2000+)
```sparql
SELECT ?aestheticName ?periodLabel ?startYear
WHERE {
  ?aesthetic a ae-ont:Aesthetic ;
             ae-ont:name ?aestheticName ;
             ae-ont:hasOriginPeriod ?period .
  ?period ae-ont:approximateLabel ?periodLabel ;
          ae-ont:startYear ?startYear .
  FILTER(str(?startYear) >= "2000")
}
ORDER BY ?startYear
LIMIT 30
```
3. **CQ3:** Which broader aesthetic/subculture does a given aesthetic belong to?
```sparql
SELECT ?subName ?parentName WHERE {
  ?parent a ae-ont:Aesthetic ; ae-ont:name ?parentName ;
          ae-ont:hasSubgenre ?sub .
  ?sub ae-ont:name ?subName .
  FILTER(str(?parentName) = "Punk")
} ORDER BY ?subName
```
4. **CQ4:** Which activities or lifestyle practices are associated with a given aesthetic?
```sparql
SELECT ?activityLabel
WHERE {
  ?aesthetic a ae-ont:Aesthetic ;
             ae-ont:name ?aestheticName ;
             ae-ont:hasAssociatedActivity ?activity .
  ?activity rdfs:label ?activityLabel .
  FILTER(str(?aestheticName) = "Cottagecore")
}
```

### 4. Relevant References
* *"Contemporary Ethnographic Aesthetics: The TikTok Turn"* [doi:10.1080/08949468.2024.2330268](https://www.tandfonline.com/doi/full/10.1080/08949468.2024.2330268)


