from rdflib import Graph, Literal, RDF, RDFS, OWL, URIRef, Namespace, XSD, BNode
from rdflib.collection import Collection

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
    # 4. ADVANCED CLASS CONSTRUCTORS (Rubric Req.)
    # ==========================================

    # A. Enumerated Class (One of {Physical, Magic, Fire...})
    # Requirement: "At least one class defined as enumeration of its individuals"
    g.add((ER.DamageType, RDF.type, OWL.Class))
    dmg_list = [ER.Physical, ER.Magic, ER.Fire, ER.Lightning, ER.Holy]
    # Define individuals
    for d in dmg_list:
        g.add((d, RDF.type, ER.DamageType))
        g.add((d, RDF.type, OWL.NamedIndividual))
    # Define enumeration
    enum_node = BNode()
    g.add((ER.DamageType, OWL.oneOf, enum_node))
    Collection(g, enum_node, dmg_list)

    # B. Union Class (Equippable = Weapon U Armor U Talisman U Shield)
    # Requirement: "At least one class defined as a union of classes"
    g.add((ER.Equippable, RDF.type, OWL.Class))
    union_node = BNode()
    g.add((ER.Equippable, OWL.unionOf, union_node))
    Collection(g, union_node, [ER.Weapon, ER.Armor, ER.Talisman, ER.Shield])

    # C. Intersection Class (HolyWeapon = Weapon AND requires Faith)
    # Requirement: "At least one class defined as an intersection of classes"
    g.add((ER.HolyWeapon, RDF.type, OWL.Class))
    intersect_node = BNode()
    
    # Restriction: requiresFaith some Integer
    faith_rest = BNode()
    g.add((faith_rest, RDF.type, OWL.Restriction))
    g.add((faith_rest, OWL.onProperty, ER.requiresFaith))
    g.add((faith_rest, OWL.someValuesFrom, XSD.integer))

    g.add((ER.HolyWeapon, OWL.intersectionOf, intersect_node))
    Collection(g, intersect_node, [ER.Weapon, faith_rest])

    # D. Complement Class (Peaceful = Complement of Boss)
    # Requirement: "At least one class defined as a complement of some class"
    g.add((ER.PeacefulEntity, RDF.type, OWL.Class))
    g.add((ER.PeacefulEntity, OWL.complementOf, ER.Boss))

    # E. Cardinality Restriction (Boss MUST drop at least 1 Item)
    # Requirement: "At least one class defined using property cardinality restrictions"
    rest_node = BNode()
    g.add((rest_node, RDF.type, OWL.Restriction))
    g.add((rest_node, OWL.onProperty, ER.drops))
    g.add((rest_node, OWL.minCardinality, Literal(1, datatype=XSD.nonNegativeInteger)))
    g.add((ER.Boss, RDFS.subClassOf, rest_node))

    # ==========================================
    # 5. PROPERTIES
    # ==========================================

    def define_prop(uri, p_type=OWL.ObjectProperty, domain=None, range=None, inverse=None, transitive=False, symmetric=False, functional=False, inverse_functional=False):
        g.add((uri, RDF.type, p_type))
        if functional: g.add((uri, RDF.type, OWL.FunctionalProperty))
        if inverse_functional: g.add((uri, RDF.type, OWL.InverseFunctionalProperty))
        
        if domain: g.add((uri, RDFS.domain, domain))
        if range: g.add((uri, RDFS.range, range))
        if inverse: 
            inv_uri = ER[inverse] if isinstance(inverse, str) else inverse
            g.add((inv_uri, RDF.type, OWL.ObjectProperty))
            g.add((uri, OWL.inverseOf, inv_uri))
        if transitive: g.add((uri, RDF.type, OWL.TransitiveProperty))
        if symmetric: g.add((uri, RDF.type, OWL.SymmetricProperty))

    # --- Object Properties ---
    define_prop(ER.locatedIn, transitive=True, range=ER.Location)
    define_prop(ER.drops, domain=ER.Agent, range=ER.Item, inverse="droppedBy")
    define_prop(ER.sells, domain=ER.Merchant, range=ER.Item, inverse="soldBy")
    define_prop(ER.hasSkill, domain=ER.Weapon, range=ER.Skill, inverse="skillOf")
    define_prop(ER.teaches, domain=ER.NPC, range=ER.Spell, inverse="taughtBy")
    define_prop(ER.mentions, inverse="mentionedIn")
    define_prop(ER.causesEffect, domain=ER.Weapon, range=ER.StatusEffect)
    define_prop(ER.hasMaxStats, domain=ER.Weapon, range=ER.StatBlock, functional=True) # A weapon has 1 stat block

    # Lore Properties
    define_prop(ER.childOf, domain=ER.Agent, range=ER.Agent, inverse="parentOf")
    define_prop(ER.siblingOf, domain=ER.Agent, range=ER.Agent, symmetric=True)
    define_prop(ER.spouseOf, domain=ER.Agent, range=ER.Agent, symmetric=True)
    define_prop(ER.memberOf, domain=ER.Agent, range=ER.Faction, inverse="hasMember")
    define_prop(ER.worships, domain=ER.Agent, range=ER.OuterGod, inverse="worshippedBy")
    define_prop(ER.participatedIn, domain=ER.Agent, range=ER.Event, inverse="hasParticipant")

    # ==========================================
    # 6. DATATYPE PROPERTIES
    # ==========================================

    # Functional Property (Requirement: "At least one object/data property should be functional")
    # Weight is unique per item.
    g.add((ER.weight, RDF.type, OWL.DatatypeProperty))
    g.add((ER.weight, RDF.type, OWL.FunctionalProperty))
    g.add((ER.weight, RDFS.range, XSD.float))

    # Inverse Functional Property (Requirement: "At least one... inverse functional")
    # The Game ID uniquely identifies the item (if we had it), or we can treat the Name as a unique key.
    # Let's create a theoretical "gameId" for compliance.
    g.add((ER.gameId, RDF.type, OWL.DatatypeProperty))
    g.add((ER.gameId, RDF.type, OWL.InverseFunctionalProperty))
    g.add((ER.gameId, RDFS.range, XSD.string))

    # Generic Stats
    stats = [
        ("hp", XSD.string), ("fpCost", XSD.integer), 
        ("hpCost", XSD.integer), ("staminaCost", XSD.integer), ("value", XSD.integer)
    ]
    for name, dtype in stats:
        uri = ER[name]
        g.add((uri, RDF.type, OWL.DatatypeProperty))
        g.add((uri, RDFS.range, dtype))

    # Attack Power & Scaling
    dmg_types = ["Physical", "Magic", "Fire", "Lightning", "Holy"]
    for dt in dmg_types:
        uri = ER[f"attack{dt}"]
        g.add((uri, RDF.type, OWL.DatatypeProperty))
        g.add((uri, RDFS.range, XSD.float))

    for attr in ["Strength", "Dexterity", "Intelligence", "Faith", "Arcane"]:
        g.add((ER[f"requires{attr}"], RDF.type, OWL.DatatypeProperty))
        g.add((ER[f"requires{attr}"], RDFS.range, XSD.integer))
        g.add((ER[f"scaling{attr}"], RDF.type, OWL.DatatypeProperty))
        g.add((ER[f"scaling{attr}"], RDFS.range, XSD.string))

    # ==========================================
    # 7. DISJOINTNESS
    # ==========================================
    members = [ER.Agent, ER.Item, ER.Location, ER.Event, ER.Faction, ER.Concept]
    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            g.add((members[i], OWL.disjointWith, members[j]))

    output_path = "rdf/elden_ring_schema.ttl"
    g.serialize(output_path, format="turtle")
    print(f"[SUCCESS] Academic Ontology generated with {len(g)} triples.")

if __name__ == "__main__":
    build_comprehensive_ontology()