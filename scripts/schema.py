from rdflib import Graph, Literal, RDF, RDFS, OWL, URIRef, Namespace, XSD

# 1. SETUP
ER = Namespace("http://www.semanticweb.org/fall2025/eldenring/")
SCHEMA = Namespace("http://schema.org/")

g = Graph()
g.bind("er", ER)
g.bind("owl", OWL)
g.bind("schema", SCHEMA)

ontology_uri = URIRef("http://www.semanticweb.org/fall2025/eldenring/")
g.add((ontology_uri, RDF.type, OWL.Ontology))
g.add((ontology_uri, RDFS.comment, Literal("The Official Elden Ring Knowledge Graph Ontology (DLC Updated)", lang="en")))

# ==========================================
# 2. CLASS HIERARCHY
# ==========================================

# --- Base Classes ---
base_classes = ["Agent", "Item", "Location", "Event", "Concept", "StatusEffect"]
for c in base_classes:
    g.add((ER[c], RDF.type, OWL.Class))

# --- Agents (Bosses & NPCs) ---
g.add((ER.Boss, RDFS.subClassOf, ER.Agent))
g.add((ER.NPC, RDFS.subClassOf, ER.Agent))
g.add((ER.Merchant, RDFS.subClassOf, ER.NPC))

# --- Items (The Big List) ---
item_subclasses = [
    "Weapon", "Shield", "Armor", "Talisman", "Consumable", 
    "Material", "KeyItem", "Remembrance", "GreatRune", 
    "SpiritAsh", "AshOfWar", "Sorcery", "Incantation", 
    "BellBearing", "Cookbook", "Whetblade", "Ammo", "Tool"
]
for c in item_subclasses:
    g.add((ER[c], RDFS.subClassOf, ER.Item))

# --- Magic Grouping ---
g.add((ER.Magic, RDF.type, OWL.Class))
g.add((ER.Sorcery, RDFS.subClassOf, ER.Magic))
g.add((ER.Incantation, RDFS.subClassOf, ER.Magic))

# --- Weapon Types (Including DLC) ---
weapon_types = [
    "Dagger", "StraightSword", "Greatsword", "ColossalSword", 
    "ThrustingSword", "HeavyThrustingSword", "CurvedSword", "CurvedGreatsword", 
    "Katana", "Twinblade", "Axe", "Greataxe", "Hammer", "GreatHammer", 
    "Flail", "Spear", "GreatSpear", "Halberd", "Reaper", "Whip", 
    "Fist", "Claw", "LightBow", "Bow", "Greatbow", "Crossbow", "Ballista", 
    "GlintstoneStaff", "SacredSeal", "Torch", 
    # DLC Types
    "HandToHandArt", "PerfumeBottle", "ThrowingBlade", "BackhandBlade", 
    "LightGreatsword", "GreatKatana", "BeastClaw"
]

for w in weapon_types:
    g.add((ER[w], RDFS.subClassOf, ER.Weapon))

# --- Armor Types ---
for a in ["Helm", "ChestArmor", "Gauntlets", "LegArmor"]:
    g.add((ER[a], RDFS.subClassOf, ER.Armor))

# --- The Shadow Node Class ---
g.add((ER.WeaponStats, RDF.type, OWL.Class))
g.add((ER.WeaponStats, RDFS.comment, Literal("A helper node containing the stats of a weapon at a specific upgrade level.")))

# ==========================================
# 3. PROPERTIES
# ==========================================

def def_prop(uri, type_, domain=None, range_=None, comment=None):
    g.add((uri, RDF.type, type_))
    if domain: g.add((uri, RDFS.domain, domain))
    if range_: g.add((uri, RDFS.range, range_))
    if comment: g.add((uri, RDFS.comment, Literal(comment)))

# --- Object Properties (Linking Nodes) ---
def_prop(ER.locatedIn, OWL.ObjectProperty, domain=ER.Agent, range_=ER.Location, comment="Where an entity can be found.")
def_prop(ER.foundIn, OWL.ObjectProperty, domain=ER.Item, range_=ER.Location, comment="Where an item can be looted.")
def_prop(ER.drops, OWL.ObjectProperty, domain=ER.Agent, range_=ER.Item, comment="What an agent drops on death.")
def_prop(ER.droppedBy, OWL.ObjectProperty, domain=ER.Item, range_=ER.Agent, comment="Inverse of drops.")
g.add((ER.drops, OWL.inverseOf, ER.droppedBy))

def_prop(ER.mentions, OWL.ObjectProperty, comment="Generic lore connection found in text descriptions.")
def_prop(ER.unlocksReward, OWL.ObjectProperty, domain=ER.Remembrance, range_=ER.Item)
def_prop(ER.sells, OWL.ObjectProperty, domain=ER.Merchant, range_=ER.Item)
def_prop(ER.hasSkill, OWL.ObjectProperty, domain=ER.Weapon, range_=ER.Skill)
def_prop(ER.causesEffect, OWL.ObjectProperty, domain=ER.Weapon, range_=ER.StatusEffect)

# --- The "Shadow Node" Property ---
def_prop(ER.hasMaxStats, OWL.ObjectProperty, domain=ER.Weapon, range_=ER.WeaponStats, 
         comment="Links a Weapon to its stats at Max Upgrade level.")

# --- Datatype Properties (Values) ---

# 1. Weapon Requirements (On the Weapon itself)
for stat in ["Strength", "Dexterity", "Intelligence", "Faith", "Arcane"]:
    def_prop(ER[f"requires{stat}"], OWL.DatatypeProperty, domain=ER.Weapon, range_=XSD.integer)

# 2. Weapon Scaling (On the WeaponStats node) - These are Strings (e.g. "S", "A")
for stat in ["Strength", "Dexterity", "Intelligence", "Faith", "Arcane"]:
    def_prop(ER[f"scaling{stat}"], OWL.DatatypeProperty, domain=ER.WeaponStats, range_=XSD.string)

# 3. Attack Power (On the WeaponStats node) - Floats
dmg_types = ["Physical", "Magic", "Fire", "Lightning", "Holy", "Stamina"]
for dt in dmg_types:
    def_prop(ER[f"attack{dt}"], OWL.DatatypeProperty, domain=ER.WeaponStats, range_=XSD.float)

# 4. General Stats
def_prop(ER.weight, OWL.DatatypeProperty, domain=ER.Item, range_=XSD.float)
def_prop(ER.healthPoints, OWL.DatatypeProperty, domain=ER.Agent, range_=XSD.integer)
def_prop(ER.runesDropped, OWL.DatatypeProperty, domain=ER.Boss, range_=XSD.integer)
def_prop(ER.description, OWL.DatatypeProperty, range_=XSD.string)

# ==========================================
# 4. SERIALIZATION
# ==========================================
outfile = "rdf/elden_ring_schema.ttl"
g.serialize(destination=outfile, format="turtle")
print(f"Generated new T-Box at {outfile} with {len(g)} triples.")