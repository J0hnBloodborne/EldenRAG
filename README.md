EldenRAG is a hybrid Retrieval-Augmented Generation engine designed to answer complex queries about Elden Ring mechanics and lore. It integrates a structured Knowledge Graph (RDF) with dense vector retrieval to provide grounded context to a local Large Language Model.

#### **The system implements a dual-retrieval strategy to handle both hard stats and unstructured lore:**
- Knowledge Graph (Structured): Game data (stats, scaling, locations) is modeled into a custom RDF ontology (rdf/elden_ring_schema.ttl). This enables deterministic SPARQL queries for specific mechanics (e.g., dual-stat scaling) that standard vector search misses.
- Semantic Search (Unstructured): A localized vector index handles natural language queries using BAAI/bge-base-en-v1.5.
- Reranking Pipeline: Retrieved candidates from both sources are scored by a Cross-Encoder (ms-marco-MiniLM-L-6-v2) to filter irrelevant context before reaching the generation phase.
- Generative Model: The system runs Qwen2.5-7B-Instruct locally (via bitsandbytes 4-bit quantization) to synthesize the final response in the persona of Melina.

Backend: Python 3.9+, FastAPI
Graph Database: RDFLib (Turtle/Triple store)
Vector Search: SentenceTransformers, PyTorch
LLM Inference: Hugging Face Transformers, BitsAndBytes (NF4 quantization)
