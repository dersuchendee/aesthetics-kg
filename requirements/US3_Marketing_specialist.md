# User Story: Marketing & Advertising Specialist

### 1. Persona
**Name:** Sofia  
**Role:** Brand Strategist / Marketing Specialist  
**Description:** Sofia works at a creative agency. Her goal is to identify emerging trends and align brand communications with the values and interests of specific digital audiences.

### 2. Scenario & Motivation
Sofia views aesthetics as powerful tools for **audience segmentation**. By understanding which aesthetic movements (like *Old Money*, *Barbiecore*, or *Frutiger Aero*) resonate with specific demographics, she can design more targeted and "culturally fluent" campaigns.

Using **AestheticsKG**, Sofia can identify potential brand alignment opportunities. She needs to know not only which visual motifs define a style, but also which **iconic figures**, **brands**, and **values** are already baked into that aesthetic's DNA. This prevents "brand-wash" and helps create authentic connections with communities.

### 3. Competency Questions & SPARQL Implementation
Sofia uses the ontology to answer these questions:

1. **CQ1:** Which iconic figures are most associated with a given aesthetic?
```sparql
SELECT ?figureLabel
WHERE {
  ?aesthetic a vibe:Aesthetic ;
             vibe:name ?aestheticName ;
             vibe:hasIconicFigure ?figure .
  ?figure rdfs:label ?figureLabel .
  FILTER(str(?aestheticName) = "Grunge")
}
```
2. **CQ2:** Which aesthetics are associated with a specific platform, and what brands are already present there?
```sparql
SELECT ?aestheticName ?brandLabel
WHERE {
  ?aesthetic a vibe:Aesthetic ;
             vibe:name ?aestheticName ;
             vibe:hasPrimaryPlatform ?platform ;
             vibe:hasRelatedBrand ?brand .
  ?platform rdfs:label ?platformLabel .
  ?brand rdfs:label ?brandLabel .
  FILTER(CONTAINS(LCASE(str(?platformLabel)), "tiktok"))
}
ORDER BY ?aestheticName
```
3. **CQ3:** Which brands are associated with a given aesthetic, and what values does it carry?
```sparql
SELECT ?brandLabel ?valueLabel WHERE {
  ?aesthetic a vibe:Aesthetic ; vibe:name "Normcore"@en .
  OPTIONAL { ?aesthetic vibe:hasRelatedBrand ?brand . ?brand rdfs:label ?brandLabel . }
  OPTIONAL {
    ?aesthetic vibe:hasMember ?value .
    ?value a vibe:Value ; rdfs:label ?valueLabel .
  }
}
```
4. **CQ4:** Which brands are representative associations of a given aesthetic?
```sparql
SELECT ?brandLabel
WHERE {
  ?aesthetic a vibe:Aesthetic ;
             vibe:name ?aestheticName ;
             vibe:hasRelatedBrand ?brand .
  ?brand rdfs:label ?brandLabel .
  FILTER(str(?aestheticName) = "Normcore")
}
ORDER BY ?brandLabel
```
