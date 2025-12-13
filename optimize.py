from rdflib import Graph
import time

print("Reading Turtle file...")
start = time.time()

g = Graph()
try:
    g.parse("elden_ring_full.ttl", format="turtle")
except Exception as e:
    print(f"Error: {e}")
    exit()

print(f"Loaded {len(g)} triples in {time.time() - start:.2f}s.")
print("Converting to N-Triples (Fast Format)...")

g.serialize(destination="elden_ring_fast.nt", format="nt")
print("Done. Use 'elden_ring_fast.nt' for validation.")