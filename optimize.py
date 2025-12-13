from rdflib import Graph
import time

print("Reading Turtle file...")
start = time.time()

g = Graph()
try:
    g.parse("elden_ring_linked.ttl", format="turtle")
except Exception as e:
    print(f"Error: {e}")
    exit()

print(f"Loaded {len(g)} triples in {time.time() - start:.2f}s.")
print("Converting to N-Triples (Fast Format)...")

g.serialize(destination="rdf/elden_ring_fast_linked.nt", format="nt")
print("Done. Use 'rdf/elden_ring_fast_linked.nt' for validation.")