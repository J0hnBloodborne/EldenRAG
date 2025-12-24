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
        print(f"ERROR: {e}")
        return

    print("--- 2. EXTRACTING ENTITIES WITH TYPES ---")
    documents = []
    
    # Renamed ?type -> ?category to avoid Python keyword conflicts
    query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
    
    SELECT DISTINCT ?entity ?label ?category ?comment WHERE {
        ?entity rdfs:label ?label .
        ?entity a ?typeClass .
        
        # 1. Ensure we only look at YOUR ontology types (ignore owl:NamedIndividual, etc.)
        FILTER(STRSTARTS(STR(?typeClass), "http://www.semanticweb.org/fall2025/eldenring/"))
        
        # 2. Extract the short name (e.g. "Katana")
        BIND(STRAFTER(STR(?typeClass), "eldenring/") AS ?category)
        
        OPTIONAL { ?entity rdfs:comment ?comment }
        
        # 3. Filter out StatBlocks/Effects
        FILTER (!regex(str(?entity), "StatBlock", "i"))
        FILTER (!regex(str(?entity), "Effect", "i"))
    }
    """
    
    for row in g.query(query):
        uri = str(row.entity)
        label = str(row.label)
        # Safely access the renamed variable
        cls_type = str(row.category) if row.category else "Item"
        desc = str(row.comment) if row.comment else ""
        
        # Inject Type into search text: "Moonveil (Katana). A sword..."
        text = f"{label} ({cls_type}). {desc}"
        
        documents.append({
            "uri": uri,
            "label": label,
            "text": text
        })
    
    print(f"   [+] Found {len(documents)} enhanced entities.")

    print(f"--- 3. EMBEDDING VECTORS ---")
    model = SentenceTransformer(MODEL_ID)
    texts = [d["text"] for d in documents]
    embeddings = model.encode(texts, convert_to_tensor=True, show_progress_bar=True)

    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
        
    with open(os.path.join(OUTPUT_DIR, "entities.json"), "w") as f:
        json.dump(documents, f)
    torch.save(embeddings, os.path.join(OUTPUT_DIR, "vectors.pt"))
    print(f"--- SUCCESS: Enhanced Index saved to {OUTPUT_DIR}/ ---")

if __name__ == "__main__":
    build_index()