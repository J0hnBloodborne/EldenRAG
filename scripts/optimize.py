from rdflib import Graph, RDF, RDFS, OWL, Namespace
import time
import os

# --- CONFIGURATION ---
INPUT_FILE = "rdf/elden_ring_linked.ttl"
OUTPUT_FILE = "rdf/elden_ring_optimized.ttl" # We stick to Turtle for readability/consistency

ER = Namespace("http://www.semanticweb.org/fall2025/eldenring/")

def expand_hierarchy(g):
    """
    Performs RDFS/OWL Reasoning (Transitive Closure).
    1. SubClass Expansion: If Katana is a Weapon, and Moonveil is a Katana -> Moonveil is a Weapon.
    2. SubProperty Expansion: (If we had 'hasBossWeapon' subPropOf 'hasWeapon', etc.)
    3. Inverse Relations: If A droppedBy B -> B drops A.
    """
    print("   [Logic] Running Rule-Based Inference...")
    
    # 1. Cache Class Hierarchy
    # subclass_map[Child] = {Parent1, Parent2}
    subclass_map = {}
    for s, o in g.subject_objects(RDFS.subClassOf):
        if s not in subclass_map: subclass_map[s] = set()
        subclass_map[s].add(o)

    # 2. Materialize Type Hierarchies (The "Moonveil is a Weapon" Fix)
    new_triples = 0
    # Iterate over all things that have a type
    # Note: We list() it to avoid changing the graph while iterating
    for s, current_type in list(g.subject_objects(RDF.type)):
        if current_type in subclass_map:
            # Add all parents
            parents = subclass_map[current_type]
            # Simple transitive lookup (limited depth for speed, or loop until saturation)
            # For this dataset, 1-2 levels is usually enough, but let's do full saturation
            queue = list(parents)
            visited = set(parents)
            
            while queue:
                parent = queue.pop(0)
                if (s, RDF.type, parent) not in g:
                    g.add((s, RDF.type, parent))
                    new_triples += 1
                
                # Check if parent has parents
                if parent in subclass_map:
                    for grand_parent in subclass_map[parent]:
                        if grand_parent not in visited:
                            visited.add(grand_parent)
                            queue.append(grand_parent)

    print(f"   [Logic] Inferred {new_triples} new class memberships.")
    
    # 3. Materialize Inverse Relations (The "Who drops this?" Fix)
    # We explicitly defined 'drops' and 'droppedBy' in converter, but let's ensure consistency
    inverse_count = 0
    if (ER.drops, OWL.inverseOf, ER.droppedBy) not in g:
        g.add((ER.drops, OWL.inverseOf, ER.droppedBy))
    
    # If A drops B, ensure B droppedBy A
    for s, o in list(g.subject_objects(ER.drops)):
        if (o, ER.droppedBy, s) not in g:
            g.add((o, ER.droppedBy, s))
            inverse_count += 1
            
    # If B droppedBy A, ensure A drops B
    for s, o in list(g.subject_objects(ER.droppedBy)):
        if (o, ER.drops, s) not in g:
            g.add((o, ER.drops, s))
            inverse_count += 1
            
    print(f"   [Logic] Synchronized {inverse_count} inverse relationships.")

def main():
    print(f"Reading {INPUT_FILE}...")
    start = time.time()

    g = Graph()
    try:
        g.parse(INPUT_FILE, format="turtle")
    except Exception as e:
        print(f"Error loading {INPUT_FILE}: {e}")
        return

    print(f"Loaded {len(g)} triples in {time.time() - start:.2f}s.")

    # --- OPTIMIZATION STEPS ---
    expand_hierarchy(g)

    # --- SERIALIZATION ---
    print(f"Serializing to {OUTPUT_FILE}...")
    # Use 'nt' (N-Triples) if speed is critical, but 'turtle' is easier to debug
    # For RAG, N-Triples is technically faster to parse, but let's stick to TTL for now.
    g.serialize(destination=OUTPUT_FILE, format="turtle")
    
    print(f"Done. Final graph size: {len(g)} triples.")

if __name__ == "__main__":
    main()