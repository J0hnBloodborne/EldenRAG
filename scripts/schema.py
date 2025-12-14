from rdflib import Graph, Literal, RDF, RDFS, OWL, URIRef, Namespace, XSD, BNode
from rdflib.collection import Collection

# 1. Setup
ER = Namespace("http://www.semanticweb.org/fall2025/eldenring/")
g = Graph()
g.bind("er", ER)
g.bind("owl", OWL)

ontology_uri = URIRef("http://www.semanticweb.org/fall2025/eldenring/")
g.add((ontology_uri, RDF.type, OWL.Ontology))

# ==========================================
# CLASSES
# ==========================================
classes = [
    "Agent", "Boss", "NPC", "Creature", "Shardbearer", "Demigod", "MinorEnemy",
    "Location", "SiteOfGrace",
    "Item", "Weapon", "Shield", "Armor", "Talisman", "Consumable", "Material", "KeyItem", "Remembrance", "GreatRune",
    "Magic", "Sorcery", "Incantation",
    "Affinity", "Attribute", "Cookbook", "Whetblade"
]
for c in classes:
    g.add((ER[c], RDF.type, OWL.Class))

# --- HIERARCHY ---
g.add((ER.Boss, RDFS.subClassOf, ER.Agent))
g.add((ER.NPC, RDFS.subClassOf, ER.Agent))
g.add((ER.Creature, RDFS.subClassOf, ER.Agent))
g.add((ER.Weapon, RDFS.subClassOf, ER.Item))
g.add((ER.Shield, RDFS.subClassOf, ER.Item))
g.add((ER.Armor, RDFS.subClassOf, ER.Item))
g.add((ER.Talisman, RDFS.subClassOf, ER.Item))
g.add((ER.Consumable, RDFS.subClassOf, ER.Item))
g.add((ER.Material, RDFS.subClassOf, ER.Item))
g.add((ER.KeyItem, RDFS.subClassOf, ER.Item))
g.add((ER.Remembrance, RDFS.subClassOf, ER.Item))
g.add((ER.GreatRune, RDFS.subClassOf, ER.Item))
g.add((ER.Cookbook, RDFS.subClassOf, ER.Item))
g.add((ER.Whetblade, RDFS.subClassOf, ER.Item))
g.add((ER.Sorcery, RDFS.subClassOf, ER.Magic))
g.add((ER.Incantation, RDFS.subClassOf, ER.Magic))

# ==========================================
# LOGICAL DEFINITIONS
# ==========================================

# 1. ENUMERATION (Affinity)
affinities = [ER.Standard, ER.Heavy, ER.Keen, ER.Quality, ER.Magic, ER.Fire]
enum_node = BNode()
Collection(g, enum_node, affinities)
g.add((ER.Affinity, OWL.oneOf, enum_node))

# 2. UNION (Magic)
union_node = BNode()
Collection(g, union_node, [ER.Sorcery, ER.Incantation])
g.add((ER.Magic, OWL.unionOf, union_node))

# 3. INTERSECTION (Demigod)
inter_node = BNode()
Collection(g, inter_node, [ER.Boss, ER.Shardbearer])
g.add((ER.Demigod, OWL.intersectionOf, inter_node))

# 4. COMPLEMENT (MinorEnemy)
not_boss = BNode()
g.add((not_boss, OWL.complementOf, ER.Boss))
compl_node = BNode()
Collection(g, compl_node, [ER.Creature, not_boss])
g.add((ER.MinorEnemy, OWL.intersectionOf, compl_node))

# ==========================================
# PROPERTIES
# ==========================================

# FIX: locatedIn Domain = Union(Agent, SiteOfGrace)
# This lets Sites of Grace be "locatedIn" a Location too.
loc_domain = BNode()
Collection(g, loc_domain, [ER.Agent, ER.SiteOfGrace])
g.add((ER.locatedIn, RDF.type, OWL.ObjectProperty))
g.add((ER.locatedIn, RDF.type, OWL.FunctionalProperty))
g.add((ER.locatedIn, RDFS.domain, loc_domain)) # <--- THE FIX
g.add((ER.locatedIn, RDFS.range, ER.Location))

# Other Props
obj_props = {
    "droppedBy": (ER.Remembrance, ER.Boss),
    "scalesWith": (ER.Weapon, ER.Attribute),
    "unlocksAffinity": (ER.Whetblade, ER.Affinity),
    "unlocksRecipeFor": (ER.Cookbook, ER.Item),
    "requiresStat": (ER.Weapon, ER.Attribute),
    "hasEffect": (ER.Talisman, XSD.string)
}
for p, (dom, rng) in obj_props.items():
    g.add((ER[p], RDF.type, OWL.ObjectProperty))
    g.add((ER[p], RDFS.domain, dom))
    g.add((ER[p], RDFS.range, rng))

g.add((ER.droppedBy, RDF.type, OWL.InverseFunctionalProperty))

# Datatype Props
data_props = ["gameId", "hasWeight", "description", "image"]
for p in data_props:
    g.add((ER[p], RDF.type, OWL.DatatypeProperty))
    g.add((ER[p], RDFS.range, XSD.float if p == "hasWeight" else (XSD.integer if p == "gameId" else XSD.string)))

g.serialize(destination="rdf/elden_ring_schema.ttl", format='turtle')
print("Fixed Schema: Sites of Grace are now connected.")