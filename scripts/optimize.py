from rdflib import Graph, RDF, RDFS, OWL, Namespace
import os

# --- CONFIGURATION ---
SCHEMA_FILE = "rdf/elden_ring_schema.ttl"  # CRITICAL: Load the rules
DATA_FILE = "rdf/elden_ring_linked.ttl"    # Load the instances
OUTPUT_FILE = "rdf/elden_ring_optimized.ttl"

ER = Namespace("http://www.semanticweb.org/fall2025/eldenring/")

def main():
    g = Graph()
    print(f"Loading Schema: {SCHEMA_FILE}")
    g.parse(SCHEMA_FILE, format="turtle") # Now it knows Katana -> Weapon
    
    print(f"Loading Data: {DATA_FILE}")
    g.parse(DATA_FILE, format="turtle")

    # Run expansion logic
    print("Running Rule-Based Inference...")
    
    # Materialize Type Hierarchies
    subclass_map = {}
    for s, o in g.subject_objects(RDFS.subClassOf):
        if s not in subclass_map: subclass_map[s] = set()
        subclass_map[s].add(o)

    new_triples = 0
    for s, current_type in list(g.subject_objects(RDF.type)):
        if current_type in subclass_map:
            for parent in subclass_map[current_type]:
                if (s, RDF.type, parent) not in g:
                    g.add((s, RDF.type, parent))
                    new_triples += 1

    # Synchronize Inverses (drops <-> droppedBy)
    inverse_count = 0
    for s, o in list(g.subject_objects(ER.drops)):
        if (o, ER.droppedBy, s) not in g:
            g.add((o, ER.droppedBy, s)); inverse_count += 1
            
    print(f"Done! Inferred {new_triples} types and {inverse_count} inverses.")
    g.serialize(destination=OUTPUT_FILE, format="turtle")

if __name__ == "__main__":
    main()