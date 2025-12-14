import networkx as nx
import matplotlib.pyplot as plt
from rdflib import Graph, RDF, RDFS, OWL, BNode
from rdflib.collection import Collection
import os

SCHEMA_FILE = "rdf/elden_ring_schema.ttl" # Path check

print(f"Generating Force-Directed 'Bubble' Diagram from {SCHEMA_FILE}...")
g = Graph()
if os.path.exists(SCHEMA_FILE):
    g.parse(SCHEMA_FILE, format="turtle")
else:
    g.parse("elden_ring_schema.ttl", format="turtle")

G = nx.DiGraph()

# --- 1. NODES (The Bubbles) ---
# We Color-Code them to make it look pro
node_colors = []
color_map = {
    "Agent": "#FF9999", "Boss": "#FF6666", "NPC": "#FFB266", # Reds/Oranges
    "Item": "#99CCFF", "Weapon": "#66B2FF", "Talisman": "#3399FF", # Blues
    "Magic": "#CC99FF", "Sorcery": "#B266FF", # Purples
    "Location": "#99FF99", "SiteOfGrace": "#66FF66" # Greens
}

for s, p, o in g.triples((None, RDF.type, OWL.Class)):
    if isinstance(s, BNode): continue
    label = s.split("/")[-1]
    if label in ["Thing", "Resource", "Class"]: continue # Remove Noise
    
    G.add_node(label)
    # Assign Color (Default to Grey if unknown)
    node_colors.append(color_map.get(label, "#E0E0E0"))

# --- 2. EDGES (The Connections) ---
# Subclass (Blue)
for s, p, o in g.triples((None, RDFS.subClassOf, None)):
    if (o, RDF.type, OWL.Class) in g and not isinstance(s, BNode) and not isinstance(o, BNode):
        src = s.split("/")[-1]; dst = o.split("/")[-1]
        if src in G.nodes and dst in G.nodes:
            G.add_edge(src, dst, label="isA", color="#888888", style="solid", weight=2)

# Properties (Red)
for s, p, o in g.triples((None, RDF.type, OWL.ObjectProperty)):
    domain = list(g.objects(s, RDFS.domain))
    range_ = list(g.objects(s, RDFS.range))
    if domain and range_:
        # Handle Union Domains
        dom_nodes = []
        if isinstance(domain[0], BNode):
            for item in Collection(g, domain[0]): dom_nodes.append(item.split("/")[-1])
        else: dom_nodes.append(domain[0].split("/")[-1])
        
        target = range_[0].split("/")[-1]
        prop_name = s.split("/")[-1]
        
        for src in dom_nodes:
            if src in G.nodes and target in G.nodes:
                G.add_edge(src, target, label=prop_name, color="red", style="solid", weight=1)

# Definitions (Green Dashed)
for s, p, o in g.triples((None, OWL.intersectionOf, None)):
    if isinstance(s, BNode): continue
    src = s.split("/")[-1]
    for item in Collection(g, o):
        if not isinstance(item, BNode):
            dst = item.split("/")[-1]
            if src in G.nodes and dst in G.nodes:
                G.add_edge(src, dst, label="Def", color="green", style="dashed", weight=3)

# --- 3. THE PHYSICS ENGINE (Spring Layout) ---
plt.figure(figsize=(16, 12))

# k = Distance between nodes (Increase to spread out)
# iterations = How long to simulate physics (50 is usually enough)
pos = nx.spring_layout(G, k=1.5, iterations=100, seed=42) 

edges = G.edges()
colors = [G[u][v].get('color', 'black') for u,v in edges]
styles = [G[u][v].get('style', 'solid') for u,v in edges]
labels = nx.get_edge_attributes(G, 'label')

# Draw Nodes (Circles)
nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=2500, edgecolors='white', linewidths=2)
nx.draw_networkx_labels(G, pos, font_size=9, font_weight="bold", font_family="sans-serif")

# Draw Edges (Curved)
nx.draw_networkx_edges(G, pos, edge_color=colors, style=styles, 
                       arrows=True, arrowsize=18, width=1.5,
                       connectionstyle="arc3,rad=0.15") # The "Organic" Curve

# Draw Labels
nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_size=8, font_color="#555555")

plt.title("Elden Ring Ontology (Force-Directed)", fontsize=16)
plt.axis("off")
plt.savefig("schema_viz.png", dpi=150, bbox_inches='tight')
print("Saved 'schema_viz.png'. This is the organic look.")
plt.show()