import os
import json
import torch
import time
from rdflib import Graph, Namespace, URIRef
from sentence_transformers import SentenceTransformer

# --- CONFIGURATION ---
GRAPH_FILE = "rdf/elden_ring_optimized.ttl"  # Input Graph
OUTPUT_DIR = "rag_index"                     # Output Folder
MODEL_ID = "BAAI/bge-base-en-v1.5"           # Embedding Model

# Define Namespaces
ER = Namespace("http://www.semanticweb.org/fall2025/eldenring/")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def build_flat_index():
    print(f"1. Loading Graph from {GRAPH_FILE}...")
    g = Graph()
    start = time.time()
    g.parse(GRAPH_FILE, format="turtle")
    print(f"   [OK] Loaded {len(g)} triples in {time.time() - start:.2f}s.")

    documents = []

    # --- SPARQL: THE DATA SMASH ---
    # We select the Entity, its Label, and Description.
    # We intentionally DO NOT select the max stats here; we handle them in Python for flexibility.
    query = """
    PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX schema: <http://schema.org/>

    SELECT DISTINCT ?entity ?label ?desc ?maxNode WHERE {
        ?entity rdfs:label ?label .
        OPTIONAL { ?entity rdfs:comment ?desc } .
        OPTIONAL { ?entity schema:description ?desc } .
        
        # KEY CHANGE: Check if this entity has a shadow stats node
        OPTIONAL { ?entity er:hasMaxStats ?maxNode } .
    }
    """
    
    print("2. Flattening Data (Joining Max Stats to Weapons)...")
    results = g.query(query)
    
    # Track processed entities to merge duplicates (since SPARQL might return rows per desc)
    processed = {}

    for row in results:
        uri = str(row.entity)
        label = str(row.label)
        desc = str(row.desc) if row.desc else ""
        max_node_uri = row.maxNode

        if uri not in processed:
            processed[uri] = {
                "subject": uri,
                "title": label,
                "text_parts": [label, f"Type: Entity", desc],
                "max_node": max_node_uri
            }
        else:
            # Append description if new
            if desc and desc not in processed[uri]["text_parts"]:
                processed[uri]["text_parts"].append(desc)

    # --- PROCESS SHADOW NODES ---
    print("3. Inlining Max Stats...")
    final_docs = []
    
    for uri, data in processed.items():
        # If we found a Max Stats Node earlier, go fetch its details now
        if data["max_node"]:
            max_stats_text = []
            # Query all properties of the shadow node
            # We skip generic RDF types to keep it clean
            for p, o in g.predicate_objects(data["max_node"]):
                prop_name = str(p).split("/")[-1]
                val = str(o).split("/")[-1]
                
                # Filter out boring stuff
                if "type" in prop_name or "label" in prop_name: continue
                
                # Format: "scalingArcane: S" -> "Scaling Arcane: S"
                readable_prop = prop_name.replace("scaling", "Scaling ").replace("requires", "Requires ")
                max_stats_text.append(f"{readable_prop} {val}")
            
            if max_stats_text:
                full_stat_block = "MAX LEVEL UPGRADE STATS: " + ", ".join(max_stats_text)
                data["text_parts"].append(full_stat_block)

        # Final Text Construction
        # We join everything into one big string. The Semantic Search will now "see" the stats.
        full_text = ". ".join(data["text_parts"])
        final_docs.append({
            "subject": data["subject"],
            "title": data["title"],
            "text": full_text
        })

    print(f"   [OK] Created {len(final_docs)} flattened documents.")

    # --- EMBEDDING ---
    print(f"4. Generating Embeddings ({MODEL_ID})...")
    model = SentenceTransformer(MODEL_ID, device="cuda" if torch.cuda.is_available() else "cpu")
    
    texts = [d["text"] for d in final_docs]
    embeddings = model.encode(texts, convert_to_tensor=True, show_progress_bar=True)

    # --- SAVE ---
    ensure_dir(OUTPUT_DIR)
    
    # Save Docs
    with open(os.path.join(OUTPUT_DIR, "docs.json"), "w", encoding="utf-8") as f:
        json.dump(final_docs, f, indent=2)
    
    # Save Embeddings
    torch.save(embeddings, os.path.join(OUTPUT_DIR, "embeddings.pt"))
    
    print(f"5. Done! Saved index to {OUTPUT_DIR}/")

if __name__ == "__main__":
    build_flat_index()