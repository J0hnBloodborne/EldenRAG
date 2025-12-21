# templates/world.py

PREFIXES = """
PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

WORLD_TEMPLATES = {
    # --- INTENT: npc_lookup (5 Templates) ---
    "npc_basic": PREFIXES + """
    SELECT DISTINCT ?role ?desc WHERE {{
        ?n a er:NPC ; rdfs:label ?name .
        FILTER(LCASE(?name) = LCASE("{name}")) .
        OPTIONAL {{ ?n er:role ?role }}
        OPTIONAL {{ ?n rdfs:comment ?desc }}
    }}""",
    
    "npc_merchant_stock": PREFIXES + """
    SELECT DISTINCT ?itemName WHERE {{
        ?n a er:NPC ; rdfs:label ?name ; er:sells ?item .
        ?item rdfs:label ?itemName .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}""",
    
    "npc_quest_reward": PREFIXES + """
    SELECT DISTINCT ?itemName WHERE {{
        ?n a er:NPC ; rdfs:label ?name ; er:givesReward ?item .
        ?item rdfs:label ?itemName .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}""",
    
    "npc_role_search": PREFIXES + """
    SELECT DISTINCT ?name WHERE {{
        ?n a er:NPC ; rdfs:label ?name ; er:role ?role .
        FILTER(CONTAINS(LCASE(?role), LCASE("{role}")))
    }} LIMIT 20""",
    
    "dead_npc_drops": PREFIXES + """
    SELECT DISTINCT ?itemName WHERE {{
        ?n a er:NPC ; rdfs:label ?name ; er:droppedBy ?item . # Inverse relation
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}""", # Note: Usually NPCs drop items, so item droppedBy NPC. 

    # --- INTENT: npc_locations (5 Templates) ---
    "npc_current_loc": PREFIXES + """
    SELECT DISTINCT ?locName WHERE {{
        ?n a er:NPC ; rdfs:label ?name ; er:locatedIn ?loc .
        ?loc rdfs:label ?locName .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}""",
    
    "npcs_by_region": PREFIXES + """
    SELECT DISTINCT ?npcName WHERE {{
        ?n a er:NPC ; rdfs:label ?npcName ; er:locatedIn ?loc .
        ?loc rdfs:label ?locName .
        FILTER(CONTAINS(LCASE(?locName), LCASE("{region}")))
    }} LIMIT 20""",
    
    "roundtable_npcs": PREFIXES + """
    SELECT DISTINCT ?npcName WHERE {{
        ?n a er:NPC ; rdfs:label ?npcName ; er:locatedIn ?loc .
        ?loc rdfs:label ?locName .
        FILTER(CONTAINS(LCASE(?locName), "roundtable"))
    }}""",
    
    "merchant_locations": PREFIXES + """
    SELECT DISTINCT ?locName ?npcName WHERE {{
        ?n a er:NPC ; rdfs:label ?npcName ; er:role "Merchant" ; er:locatedIn ?loc .
        ?loc rdfs:label ?locName .
    }} LIMIT 20""",
    
    "trainer_locations": PREFIXES + """
    SELECT DISTINCT ?locName ?npcName WHERE {{
        ?n a er:NPC ; rdfs:label ?npcName ; er:role "Trainer" ; er:locatedIn ?loc .
        ?loc rdfs:label ?locName .
    }} LIMIT 20""",

    # --- INTENT: location_items (10 Templates) ---
    "items_in_specific_loc": PREFIXES + """
    SELECT DISTINCT ?itemName WHERE {{
        ?item er:foundIn ?loc ; rdfs:label ?itemName .
        ?loc rdfs:label ?locName .
        FILTER(LCASE(?locName) = LCASE("{location}"))
    }} LIMIT 20""",
    
    "key_items_in_region": PREFIXES + """
    SELECT DISTINCT ?itemName ?locName WHERE {{
        ?item a er:KeyItem ; er:foundIn ?loc ; rdfs:label ?itemName .
        ?loc rdfs:label ?locName .
        FILTER(CONTAINS(LCASE(?locName), LCASE("{region}")))
    }} LIMIT 20""",
    
    "seeds_in_region": PREFIXES + """
    SELECT DISTINCT ?locName WHERE {{
        ?item rdfs:label "Golden Seed" ; er:foundIn ?loc .
        ?loc rdfs:label ?locName .
        FILTER(CONTAINS(LCASE(?locName), LCASE("{region}")))
    }}""",
    
    "tears_in_region": PREFIXES + """
    SELECT DISTINCT ?locName WHERE {{
        ?item rdfs:label "Sacred Tear" ; er:foundIn ?loc .
        ?loc rdfs:label ?locName .
        FILTER(CONTAINS(LCASE(?locName), LCASE("{region}")))
    }}""",
    
    "cookbooks_in_region": PREFIXES + """
    SELECT DISTINCT ?bookName ?locName WHERE {{
        ?b a er:Cookbook ; rdfs:label ?bookName ; er:foundIn ?loc .
        ?loc rdfs:label ?locName .
        FILTER(CONTAINS(LCASE(?locName), LCASE("{region}")))
    }}""",
    
    "talismans_in_dungeon": PREFIXES + """
    SELECT DISTINCT ?tName ?dName WHERE {{
        ?t a er:Talisman ; rdfs:label ?tName ; er:foundIn ?loc .
        ?loc rdfs:label ?dName .
        FILTER(CONTAINS(LCASE(?dName), "catacombs") || CONTAINS(LCASE(?dName), "cave"))
    }} LIMIT 20""",
    
    "spells_in_region": PREFIXES + """
    SELECT DISTINCT ?spellName WHERE {{
        { ?s a er:Sorcery } UNION { ?s a er:Incantation } .
        ?s rdfs:label ?spellName ; er:foundIn ?loc .
        ?loc rdfs:label ?locName .
        FILTER(CONTAINS(LCASE(?locName), LCASE("{region}")))
    }} LIMIT 20""",
    
    "bell_bearings_in_region": PREFIXES + """
    SELECT DISTINCT ?bbName WHERE {{
        ?b a er:BellBearing ; rdfs:label ?bbName ; er:foundIn ?loc .
        ?loc rdfs:label ?locName .
        FILTER(CONTAINS(LCASE(?locName), LCASE("{region}")))
    }}""",
    
    "ashes_in_region": PREFIXES + """
    SELECT DISTINCT ?ashName WHERE {{
        ?a a er:SpiritAsh ; rdfs:label ?ashName ; er:foundIn ?loc .
        ?loc rdfs:label ?locName .
        FILTER(CONTAINS(LCASE(?locName), LCASE("{region}")))
    }} LIMIT 20""",
    
    "maps_in_region": PREFIXES + """
    SELECT DISTINCT ?mapName WHERE {{
        ?m rdfs:label ?mapName ; er:foundIn ?loc .
        ?loc rdfs:label ?locName .
        FILTER(CONTAINS(LCASE(?mapName), "map fragment"))
        FILTER(CONTAINS(LCASE(?locName), LCASE("{region}")))
    }}"""
}