import os
import json
import torch
import time
from rdflib import Graph, Namespace, URIRef
from sentence_transformers import SentenceTransformer

# --- CONFIGURATION ---
GRAPH_FILE = "rdf/elden_ring_optimized.ttl"
OUTPUT_DIR = "rag_index"
MODEL_ID = "BAAI/bge-base-en-v1.5"

def build_flat_index():
    print(f"1. Loading Optimized Graph...")
    g = Graph()
    g.parse(GRAPH_FILE, format="turtle")

    # This dictionary will hold our "Enhanced Records"
    # Format: { URI: { "title": str, "content_parts": [] } }
    master_index = {}

    # STEP A: Core Labels and Descriptions
    print("2. Extracting Core Descriptions...")
    core_query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?entity ?label ?desc WHERE {
        ?entity rdfs:label ?label .
        OPTIONAL { ?entity rdfs:comment ?desc } .
    }
    """
    for row in g.query(core_query):
        uri = str(row.entity)
        master_index[uri] = {
            "title": str(row.label),
            "text": [f"Name: {row.label}", f"Description: {row.desc or 'No description available.'}"]
        }

    # STEP B: Relational Inlining (The "Secret Sauce")
    # We find every URI connected to our entity and grab its human label
    print("3. Inlining Graph Relationships...")
    rel_query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?entity ?propLabel ?objLabel WHERE {
        ?entity ?p ?obj .
        ?p rdfs:label ?propLabel .
        ?obj rdfs:label ?objLabel .
        FILTER(!isLiteral(?obj))
    }
    """
    for row in g.query(rel_query):
        uri = str(row.entity)
        if uri in master_index:
            # e.g., "Located In: Limgrave" or "Dropped By: Magma Wyrm"
            master_index[uri]["text"].append(f"{row.propLabel}: {row.objLabel}")

    # Finalize documents
    final_docs = []
    for uri, data in master_index.items():
        final_docs.append({
            "subject": uri,
            "title": data["title"],
            "text": ". ".join(data["text"])
        })

    print(f"4. Embedding {len(final_docs)} enhanced documents...")
    model = SentenceTransformer(MODEL_ID)
    texts = [d["text"] for d in final_docs]
    embeddings = model.encode(texts, convert_to_tensor=True, show_progress_bar=True)

    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    with open(os.path.join(OUTPUT_DIR, "docs.json"), "w") as f:
        json.dump(final_docs, f, indent=2)
    torch.save(embeddings, os.path.join(OUTPUT_DIR, "embeddings.pt"))
    print("Done!")

if __name__ == "__main__":
    build_flat_index()