# EldenRAG: Elden Ring Knowledge Graph & Semantic Reasoning System

**Course:** AI-311 | **Instructor:** Dr. Khurram Jadoon

**Group:** 4
**Members:** 2023073, 2023495, 2023574

## Project Overview
**EldenRAG** is a semantic web project that transforms unstructured *Elden Ring* game data into a highly interconnected **Knowledge Graph**. By leveraging **OWL 2 Ontologies**, **SPARQL**, and **LLMs**, this system enables complex reasoning that standard wikis cannot perform (e.g., "Find all weapons that scale with Intelligence, cause Bleed, and are located in Caelid").

This repository contains the complete pipeline:
1.  **Ontology Design (T-Box):** A formal schema defining 50+ classes and 20+ properties.
2.  **ETL Pipeline:** Python scripts to convert CSV data into RDF/Turtle format.
3.  **Reasoning Engine:** Scripts to materialize inferences (e.g., drops -> droppedBy).
4.  **Semantic Search Agent (Bonus):** A Graph-Augmented Generation (Graph-RAG) chatbot that answers natural language questions using verified SPARQL data.

---

## Repository Structure

| File/Folder | Description | Rubric Mapping |
| :--- | :--- | :--- |
| `rdf/elden_ring_schema.ttl` | The core Ontology definition (Classes, Properties, Restrictions). | **M3 / Rubric #4** |
| `rdf/elden_ring_optimized.ttl` | The full Knowledge Graph with 5,000+ materialized triples. | **Rubric #11** |
| `rdf/manual_test.ttl` | Small dataset for manual reasoning validation. | **M3 Requirement** |
| `scripts/schema.py` | Generates the T-Box (Ontology Schema) using Python/RDFLib. | **Rubric #7** |
| `scripts/converter.py` | ETL script that maps raw CSVs to RDF triples (A-Box). | **Rubric #7** |
| `scripts/optimize.py` | Applies reasoning rules to materialize the graph. | **Rubric #10** |
| `scripts/competency.py` | Python script executing federated SPARQL queries. | **Rubric #13** |
| `web_server.py` | FastAPI backend for the Graph-RAG Chatbot. | **Rubric #14 (Bonus)** |
| `graph_agent.py` | Logic for the semantic agent. | **Rubric #14 (Bonus)** |
| `data/` | Raw CSV source files. | -- |

---

## Installation & Setup

### 1. Prerequisites
* Python 3.9+
* GraphDB or OpenLink Virtuoso (Optional, for GUI visualization)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. (Optional) Re-Generate the Graph
If you want to build the graph from scratch using the raw CSVs, run the pipeline in this order:

```bash

# 1. Generate the T-Box (Schema/Ontology)
python scripts/schema.py

# 2. Convert CSVs to raw RDF (A-Box)
python scripts/converter.py

# 3. Link entities to Wikidata (5-Star Linked Data)
python scripts/linker.py

# 4. Run Reasoner to materialize inferences (Final Optimization)
python scripts/optimize.py
Output: rdf/elden_ring_optimized.ttl
```

### 4. Validation & Usage

A. Run Competency Questions (Rubric #13)
To validate the graph against the project requirements, run the automated SPARQL script. This executes complex queries including multi-hop pathfinding and transitive lookups.

```bash
python scripts/competency.py
```

B. Run the Semantic Chatbot (Rubric #14 - Bonus)
This starts a local web server that uses the Knowledge Graph to answer natural language questions.

Start the server:

```bash
python web_server.py
```
Open your browser to http://localhost:5000

Ask a question like: "Where can I find the Moonveil Katana and what are its stats?"

### 5. Technical Highlights
Reasoning: Uses owlrl and custom logic to infer inverse relationships and class membership (e.g., classifying a Boss as a Shardbearer based on their drops).

Linked Data: Entities are aligned with Wikidata URIs to achieve 5-Star Linked Data status.

Graph-RAG: The chatbot does not rely solely on LLM training data; it queries the local ontology to prevent hallucinations.