from rdflib import Graph, Literal, RDF, RDFS, OWL, URIRef, Namespace, XSD

# 1. NAMESPACES
ER = Namespace("http://www.semanticweb.org/fall2025/eldenring/")
SCHEMA = Namespace("http://schema.org/")

def build_comprehensive_ontology():
    g = Graph()
    g.bind("er", ER)
    g.bind("owl", OWL)
    g.bind("schema", SCHEMA)

    # 2. ONTOLOGY DEFINITION
    ontology_uri = ER[""]
    g.add((ontology_uri, RDF.type, OWL.Ontology))
    g.add((ontology_uri, RDFS.comment, Literal("Comprehensive Elden Ring Ontology: Production Gameplay & Full Lore", lang="en")))

    # ==========================================
    # 3. CLASS HIERARCHY
    # ==========================================
    
    # --- Base Classes ---
    base_classes = [
        "Agent", "Item", "Location", "Skill", "StatusEffect", 
        "Event", "Concept", "StatBlock", "Faction", "OuterGod", "Family"
    ]
    for c in base_classes:
        g.add((ER[c], RDF.type, OWL.Class))

    # --- Agent Subclasses ---
    g.add((ER.Boss, RDFS.subClassOf, ER.Agent))
    g.add((ER.NPC, RDFS.subClassOf, ER.Agent))
    g.add((ER.Creature, RDFS.subClassOf, ER.Agent))
    g.add((ER.Merchant, RDFS.subClassOf, ER.NPC))
    g.add((ER.Demigod, RDFS.subClassOf, ER.Agent))
    g.add((ER.Empyrean, RDFS.subClassOf, ER.Agent))

    # --- Item Subclasses ---
    item_types = [
        "Weapon", "Shield", "Armor", "Talisman", "Spell", "SpiritAsh", 
        "Consumable", "Material", "KeyItem", "Ammo", "AshOfWar", "Tool", 
        "Remembrance", "GreatRune", "CrystalTear", "Cookbook", "BellBearing", "Whetblade"
    ]
    for t in item_types:
        g.add((ER[t], RDFS.subClassOf, ER.Item))
    
    g.add((ER.Sorcery, RDFS.subClassOf, ER.Spell))
    g.add((ER.Incantation, RDFS.subClassOf, ER.Spell))

    # --- Location Subclasses ---
    loc_types = [
        "Region", "Dungeon", "SiteOfGrace", "Ruins", "Cave", 
        "Catacombs", "Evergaol", "Tower", "Fort", "Castle"
    ]
    for t in loc_types:
        g.add((ER[t], RDFS.subClassOf, ER.Location))

    # ==========================================
    # 4. PROPERTIES
    # ==========================================

    def define_prop(uri, p_type=OWL.ObjectProperty, domain=None, range=None, inverse=None, transitive=False, symmetric=False):
        g.add((uri, RDF.type, p_type))
        if domain: g.add((uri, RDFS.domain, domain))
        if range: g.add((uri, RDFS.range, range))
        if inverse: 
            inv_uri = ER[inverse] if isinstance(inverse, str) else inverse
            g.add((inv_uri, RDF.type, OWL.ObjectProperty))
            g.add((uri, OWL.inverseOf, inv_uri))
        if transitive: g.add((uri, RDF.type, OWL.TransitiveProperty))
        if symmetric: g.add((uri, RDF.type, OWL.SymmetricProperty))

    # --- Connections ---
    define_prop(ER.locatedIn, transitive=True, range=ER.Location)
    define_prop(ER.drops, domain=ER.Agent, range=ER.Item, inverse="droppedBy")
    define_prop(ER.sells, domain=ER.Merchant, range=ER.Item, inverse="soldBy")
    define_prop(ER.hasSkill, domain=ER.Weapon, range=ER.Skill, inverse="skillOf")
    define_prop(ER.teaches, domain=ER.NPC, range=ER.Spell, inverse="taughtBy")
    define_prop(ER.containsItem, domain=ER.Location, range=ER.Item, inverse="foundAt")
    define_prop(ER.mentions, inverse="mentionedIn")
    define_prop(ER.causesEffect, domain=ER.Weapon, range=ER.StatusEffect)
    define_prop(ER.hasMaxStats, domain=ER.Weapon, range=ER.StatBlock)

    # --- Lore Properties ---
    define_prop(ER.childOf, domain=ER.Agent, range=ER.Agent, inverse="parentOf")
    define_prop(ER.siblingOf, domain=ER.Agent, range=ER.Agent, symmetric=True)
    define_prop(ER.spouseOf, domain=ER.Agent, range=ER.Agent, symmetric=True)
    define_prop(ER.descendantOf, domain=ER.Agent, range=ER.Agent, transitive=True)
    define_prop(ER.alliedWith, domain=ER.Agent, range=ER.Agent, symmetric=True)
    define_prop(ER.enemyOf, domain=ER.Agent, range=ER.Agent, symmetric=True)
    define_prop(ER.memberOf, domain=ER.Agent, range=ER.Faction, inverse="hasMember")
    define_prop(ER.servantOf, domain=ER.Agent, range=ER.Agent, inverse="hasServant")
    define_prop(ER.worships, domain=ER.Agent, range=ER.OuterGod, inverse="worshippedBy")
    define_prop(ER.participatedIn, domain=ER.Agent, range=ER.Event, inverse="hasParticipant")
    define_prop(ER.associatedWith, domain=ER.Item, range=ER.Concept)

    # ==========================================
    # 5. DATATYPE PROPERTIES (Hard Stats)
    # ==========================================

    # Generic Stats
    stats = [
        ("weight", XSD.float), ("hp", XSD.string), ("fpCost", XSD.integer), 
        ("hpCost", XSD.integer), ("staminaCost", XSD.integer), ("value", XSD.integer)
    ]
    for name, dtype in stats:
        uri = ER[name]
        g.add((uri, RDF.type, OWL.DatatypeProperty))
        g.add((uri, RDFS.range, dtype))

    # Attack Power Stats (Added for StatBlock)
    dmg_types = ["Physical", "Magic", "Fire", "Lightning", "Holy"]
    for dt in dmg_types:
        uri = ER[f"attack{dt}"]
        g.add((uri, RDF.type, OWL.DatatypeProperty))
        g.add((uri, RDFS.range, XSD.float))

    # Requirements & Scaling
    for attr in ["Strength", "Dexterity", "Intelligence", "Faith", "Arcane"]:
        g.add((ER[f"requires{attr}"], RDF.type, OWL.DatatypeProperty))
        g.add((ER[f"requires{attr}"], RDFS.range, XSD.integer))
        
        g.add((ER[f"scaling{attr}"], RDF.type, OWL.DatatypeProperty))
        g.add((ER[f"scaling{attr}"], RDFS.range, XSD.string))

    # ==========================================
    # 6. LOGICAL AXIOMS
    # ==========================================
    members = [ER.Agent, ER.Item, ER.Location, ER.Event, ER.Faction, ER.Concept]
    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            g.add((members[i], OWL.disjointWith, members[j]))

    output_path = "rdf/elden_ring_schema.ttl"
    g.serialize(output_path, format="turtle")
    print(f"[SUCCESS] Ontology generated with {len(g)} triples.")

if __name__ == "__main__":
    build_comprehensive_ontology()