import os
import json
import torch
from rdflib import Graph
from sentence_transformers import SentenceTransformer

# --- CONFIG ---
GRAPH_FILE = "rdf/elden_ring_optimized.ttl"
OUTPUT_DIR = "rag_index"
MODEL_ID = "BAAI/bge-small-en-v1.5" 

def build_index():
    print(f"--- 1. LOADING GRAPH ---")
    g = Graph()
    try:
        g.parse(GRAPH_FILE, format="turtle")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return

    print("--- 2. EXTRACTING ONLY 'REAL' ENTITIES ---")
    documents = []
    
    # STRICT QUERY: Only grab items that act as "Main Pages"
    # We explicitly exclude anything that looks like a StatBlock or generic node
    query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
    
    SELECT DISTINCT ?entity ?label ?comment WHERE {
        ?entity rdfs:label ?label .
        OPTIONAL { ?entity rdfs:comment ?comment }
        
        # Filter out the noise
        FILTER (!regex(str(?entity), "StatBlock", "i"))
        FILTER (!regex(str(?entity), "Effect", "i"))
    }
    """
    
    for row in g.query(query):
        uri = str(row.entity)
        label = str(row.label)
        desc = str(row.comment) if row.comment else ""
        text = f"{label}. {desc}"
        
        documents.append({
            "uri": uri,
            "label": label,
            "text": text
        })
    
    print(f"   [+] Found {len(documents)} clean entities (No StatBlocks).")

    print(f"--- 3. EMBEDDING VECTORS ---")
    model = SentenceTransformer(MODEL_ID)
    texts = [d["text"] for d in documents]
    embeddings = model.encode(texts, convert_to_tensor=True, show_progress_bar=True)

    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
        
    with open(os.path.join(OUTPUT_DIR, "entities.json"), "w") as f:
        json.dump(documents, f)
    torch.save(embeddings, os.path.join(OUTPUT_DIR, "vectors.pt"))
    print(f"--- SUCCESS: Clean Index saved to {OUTPUT_DIR}/ ---")

if __name__ == "__main__":
    build_index()