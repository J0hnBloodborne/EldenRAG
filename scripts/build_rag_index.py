import os
import re
import shutil
from rdflib import Graph, URIRef, Literal, Namespace, RDF  # <--- Added RDF here
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document 
from tqdm import tqdm

# --- CONFIGURATION ---
INPUT_FILE = "rdf/elden_ring_optimized.ttl"
DB_DIR = "data/chroma_db"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2" 

ER = Namespace("http://www.semanticweb.org/fall2025/eldenring/")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
SCHEMA = Namespace("http://schema.org/")

def format_name(uri_or_str):
    """Clean up URI fragments like 'scalingIntelligence' -> 'Scaling Intelligence'"""
    s = str(uri_or_str).split("/")[-1]
    # Split camelCase
    s = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', s)
    s = re.sub('([a-z0-9])([A-Z])', r'\1 \2', s)
    return s

def build_entity_cards(g):
    print("   [Indexer] Transforming Graph into Rich Entity Cards (With Deep Stats)...")
    documents = []
    
    # Only index main entities (things with a Label)
    subjects = list(g.subjects(RDFS.label, None))
    
    for subj in tqdm(subjects, desc="Processing Entities"):
        content_parts = []
        metadata = {"id": str(subj)}
        
        # 1. HEADER (Name & Type)
        name = g.value(subj, RDFS.label)
        if not name: continue
        content_parts.append(f"Entity: {name}")
        metadata["name"] = str(name)
        
        types = [str(g.value(o, RDFS.label)) if g.value(o, RDFS.label) else o.split("/")[-1] 
                 for o in g.objects(subj,  URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"))]
        if types:
            content_parts.append(f"Type: {', '.join(types)}")
            metadata["type"] = types[0]

        # 2. DESCRIPTION
        desc = g.value(subj, RDFS.comment) or g.value(subj, SCHEMA.description)
        if desc:
            content_parts.append(f"Description: {desc}")

        # 3. PROPERTIES & DEEP STATS
        stats = []
        lore_mentions = []
        
        # Iterate all properties of the main subject
        for p, o in g.predicate_objects(subj):
            # FIX: RDF is now imported so RDF.type works
            if p in [RDFS.label, RDFS.comment, SCHEMA.description, SCHEMA.image, RDF.type]: continue
            
            p_name = format_name(p)
            
            # A. HANDLE SHADOW NODES (Recursion)
            if "hasMaxStats" in str(p):
                # The object 'o' is the Shadow Node (e.g., Moonveil_MaxStandard)
                path = g.value(o, ER.upgradePath)
                if not path: path = "Standard"
                
                shadow_stats = []
                for sp, so in g.predicate_objects(o):
                    if sp == ER.upgradePath or sp == RDF.type: continue
                    sp_name = format_name(sp)
                    shadow_stats.append(f"{sp_name}: {so}")
                
                # Inline this block into the main card
                stats.append(f"Max Upgrade Stats ({path} Path): {', '.join(shadow_stats)}")
                continue

            # B. HANDLE LORE MENTIONS
            if "mentions" in str(p).lower():
                mentioned_name = g.value(o, RDFS.label)
                if mentioned_name: lore_mentions.append(str(mentioned_name))
                continue

            # C. STANDARD PROPERTIES
            val = str(o)
            if isinstance(o, URIRef):
                label = g.value(o, RDFS.label)
                val = str(label) if label else format_name(o)
            
            stats.append(f"{p_name}: {val}")
            
        if stats:
            content_parts.append("Properties & Stats:\n- " + "\n- ".join(stats))
        if lore_mentions:
            content_parts.append(f"Lore Connections: Mentions {', '.join(lore_mentions)}")

        # 4. CONTEXT (Incoming Links)
        incoming = []
        for s, p in g.subject_predicates(subj):
            s_name = g.value(s, RDFS.label)
            if s_name:
                p_name = format_name(p)
                incoming.append(f"{s_name} ({p_name} this)")
        
        if incoming:
            if len(incoming) > 15: # Cap context to prevent noise
                content_parts.append(f"World Context: Linked to {len(incoming)} entities including {', '.join(incoming[:10])}...")
            else:
                content_parts.append(f"World Context: {'; '.join(incoming)}")

        # Create Document
        documents.append(Document(page_content="\n".join(content_parts), metadata=metadata))

    return documents

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    g = Graph()
    g.parse(INPUT_FILE, format="turtle")
    print(f"Graph loaded: {len(g)} triples.")

    docs = build_entity_cards(g)
    print(f"Generated {len(docs)} Rich Entity Cards.")

    print(f"Ingesting into ChromaDB ({EMBEDDING_MODEL})...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    # Clear old DB if exists to avoid duplicates
    if os.path.exists(DB_DIR):
        shutil.rmtree(DB_DIR)
        
    # Batch Ingest
    batch_size = 500
    for i in range(0, len(docs), batch_size):
        batch = docs[i : i + batch_size]
        Chroma.from_documents(batch, embeddings, persist_directory=DB_DIR)
        print(f"   Indexed {min(i + batch_size, len(docs))}/{len(docs)}...")

    print("Done. The Brain is fully operational.")

if __name__ == "__main__":
    main()