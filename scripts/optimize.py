from rdflib import Graph, RDF, RDFS, OWL, Namespace
import os

# --- CONFIGURATION ---
SCHEMA_FILE = "rdf/elden_ring_schema.ttl"  # The Rules
DATA_FILE = "rdf/elden_ring_linked.ttl"    # The Data (Post-Linker)
OUTPUT_FILE = "rdf/elden_ring_optimized.ttl" # Final RAG-ready file

ER = Namespace("http://www.semanticweb.org/fall2025/eldenring/")

def main():
    print("--- STARTING GRAPH OPTIMIZATION ---")
    
    # 1. Load the Graphs
    g = Graph()
    print(f"1. Loading Schema: {SCHEMA_FILE}...")
    g.parse(SCHEMA_FILE, format="turtle") 
    
    print(f"2. Loading Data: {DATA_FILE}...")
    g.parse(DATA_FILE, format="turtle")
    
    initial_len = len(g)
    print(f"   [Stats] Initial Triples: {initial_len}")

    # 2. INFERENCE: Materialize Subclasses
    # If "Katana" is a subclass of "Weapon", make every Katana a Weapon.
    print("3. Materializing Types (SubClassOf)...")
    subclass_map = {}
    for s, o in g.subject_objects(RDFS.subClassOf):
        if s not in subclass_map: subclass_map[s] = set()
        subclass_map[s].add(o)

    type_count = 0
    # Iterate over every entity that has a type
    for s, current_type in list(g.subject_objects(RDF.type)):
        if current_type in subclass_map:
            for parent in subclass_map[current_type]:
                if (s, RDF.type, parent) not in g:
                    g.add((s, RDF.type, parent))
                    type_count += 1
    print(f"   [+] Inferred {type_count} new type classifications.")

    # 3. INFERENCE: Synchronize Inverses (Generic)
    # Instead of hardcoding 'drops', we look at the Schema for ALL inverses.
    print("4. Synchronizing Inverses (Schema-Aware)...")
    
    # Find all pairs: (?p1 owl:inverseOf ?p2)
    inverse_pairs = []
    for p1, p2 in g.subject_objects(OWL.inverseOf):
        inverse_pairs.append((p1, p2))
        # Ensure bidirectionality in our logic check
        inverse_pairs.append((p2, p1))
    
    inv_count = 0
    for p1, p2 in set(inverse_pairs):
        # For every triple using Property 1...
        for s, o in list(g.subject_objects(p1)):
            # ...add the reverse triple using Property 2
            if (o, p2, s) not in g:
                g.add((o, p2, s))
                inv_count += 1

    print(f"   [+] Inferred {inv_count} inverse relationships (e.g., parentOf, droppedBy).")

    # 4. Save
    print(f"5. Saving to {OUTPUT_FILE}...")
    g.serialize(destination=OUTPUT_FILE, format="turtle")
    print(f"--- DONE. Final Graph Size: {len(g)} triples (+{len(g)-initial_len}) ---")

if __name__ == "__main__":
    main()