from rdflib import Graph, Literal, RDF, RDFS, OWL, URIRef, Namespace, XSD, BNode
from rdflib.collection import Collection

# 1. Setup
ER = Namespace("http://www.semanticweb.org/fall2025/eldenring/")
WD = Namespace("http://www.wikidata.org/entity/") # External Link
g = Graph()
g.bind("er", ER)
g.bind("owl", OWL)
g.bind("wd", WD)

ontology_uri = URIRef("http://www.semanticweb.org/fall2025/eldenring/")
g.add((ontology_uri, RDF.type, OWL.Ontology))

# --- CLASSES ---
classes = [
    "Agent", "Boss", "NPC", "Creature", "Shardbearer",
    "Location", "Item", "Weapon", "Armor", "Talisman", "Remembrance",
    "Affinity", "Attribute", "Cookbook", "Whetblade"
]
for c in classes:
    g.add((ER[c], RDF.type, OWL.Class))

# --- HIERARCHY ---
g.add((ER.Boss, RDFS.subClassOf, ER.Agent))
g.add((ER.NPC, RDFS.subClassOf, ER.Agent))
g.add((ER.Creature, RDFS.subClassOf, ER.Agent))
g.add((ER.Weapon, RDFS.subClassOf, ER.Item))
g.add((ER.Remembrance, RDFS.subClassOf, ER.Item))

# --- RUBRIC REQUIREMENT: ENUMERATION ---
# Class 'Affinity' is defined as specific individuals only
affinities = [ER.Standard, ER.Heavy, ER.Keen, ER.Quality, ER.Magic, ER.Fire]
g.add((ER.Affinity, RDF.type, OWL.Class))
enum_node = BNode()
Collection(g, enum_node, affinities)
g.add((ER.Affinity, OWL.oneOf, enum_node))

# --- RUBRIC REQUIREMENT: INTERSECTION ---
# Demigod = Boss AND Shardbearer
demigod = ER.Demigod
g.add((demigod, RDF.type, OWL.Class))
inter_node = BNode()
Collection(g, inter_node, [ER.Boss, ER.Shardbearer])
g.add((demigod, OWL.intersectionOf, inter_node))

# --- RUBRIC REQUIREMENT: COMPLEMENT ---
# MinorEnemy = Creature AND (NOT Boss)
minor_enemy = ER.MinorEnemy
g.add((minor_enemy, RDF.type, OWL.Class))
# Define NOT Boss
not_boss = BNode()
g.add((not_boss, OWL.complementOf, ER.Boss))
# Define Intersection
compl_inter_node = BNode()
Collection(g, compl_inter_node, [ER.Creature, not_boss])
g.add((minor_enemy, OWL.intersectionOf, compl_inter_node))

# --- PROPERTIES ---

# 1. Functional Property (Rubric)
# An agent can only be primarily located in one place
p_loc = ER.locatedIn
g.add((p_loc, RDF.type, OWL.ObjectProperty))
g.add((p_loc, RDF.type, OWL.FunctionalProperty))
g.add((p_loc, RDFS.domain, ER.Agent))
g.add((p_loc, RDFS.range, ER.Location))

# 2. Inverse Functional Property (Rubric)
# A specific Remembrance uniquely identifies the Boss who dropped it
p_rem = ER.droppedBy
g.add((p_rem, RDF.type, OWL.ObjectProperty))
g.add((p_rem, RDF.type, OWL.InverseFunctionalProperty))
g.add((p_rem, RDFS.domain, ER.Remembrance))
g.add((p_rem, RDFS.range, ER.Boss))

# 3. Standard Properties with Ranges (Rubric)
props = {
    "scalesWith": (ER.Weapon, ER.Attribute),
    "unlocksAffinity": (ER.Whetblade, ER.Affinity),
    "unlocksRecipeFor": (ER.Cookbook, ER.Item)
}
for p_name, (dom, rng) in props.items():
    p = ER[p_name]
    g.add((p, RDF.type, OWL.ObjectProperty))
    g.add((p, RDFS.domain, dom))
    g.add((p, RDFS.range, rng))

# 4. Datatype Properties
g.add((ER.gameId, RDF.type, OWL.DatatypeProperty))
g.add((ER.gameId, RDFS.range, XSD.integer))
g.add((ER.hasWeight, RDF.type, OWL.DatatypeProperty))
g.add((ER.hasWeight, RDFS.range, XSD.float))

# Output
g.serialize(destination="elden_ring_schema.ttl", format='turtle')
print("T-Box Generated.")