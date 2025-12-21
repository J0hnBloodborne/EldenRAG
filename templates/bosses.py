# templates/bosses.py

PREFIXES = """
PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

BOSS_TEMPLATES = {
    # --- INTENT: boss_lookup (5 Templates) ---
    "boss_basic": PREFIXES + """
    SELECT DISTINCT ?desc ?hp ?runes WHERE {{
        ?b a er:Boss ; rdfs:label ?name .
        FILTER(LCASE(?name) = LCASE("{name}")) .
        OPTIONAL {{ ?b rdfs:comment ?desc }}
        OPTIONAL {{ ?b er:healthPoints ?hp }}
        OPTIONAL {{ ?b er:runesDropped ?runes }}
    }}""",
    
    "boss_health_only": PREFIXES + """
    SELECT DISTINCT ?hp WHERE {{
        ?b a er:Boss ; rdfs:label ?name ; er:healthPoints ?hp .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}""",
    
    "boss_runes_only": PREFIXES + """
    SELECT DISTINCT ?runes WHERE {{
        ?b a er:Boss ; rdfs:label ?name ; er:runesDropped ?runes .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}""",
    
    "legend_boss_lookup": PREFIXES + """
    SELECT DISTINCT ?name ?desc WHERE {{
        ?b a er:Boss ; rdfs:label ?name ; rdfs:comment ?desc .
        FILTER(CONTAINS(LCASE(?desc), "legend") || CONTAINS(LCASE(?desc), "demigod"))
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}""",
    
    "boss_alias_lookup": PREFIXES + """
    SELECT DISTINCT ?alias WHERE {{
        ?b a er:Boss ; rdfs:label ?name ; er:alias ?alias .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}""",

    # --- INTENT: boss_drops (10 Templates) ---
    
    "all_drops": PREFIXES + """
    SELECT DISTINCT ?itemName WHERE {{
        ?item er:droppedBy ?boss ; rdfs:label ?itemName .
        ?boss rdfs:label ?bossName .
        FILTER(LCASE(?bossName) = LCASE("{name}"))
    }}""",
    
    "weapon_drops_only": PREFIXES + """
    SELECT DISTINCT ?itemName WHERE {{
        ?item er:droppedBy ?boss ; rdfs:label ?itemName ; a er:Weapon .
        ?boss rdfs:label ?bossName .
        FILTER(LCASE(?bossName) = LCASE("{name}"))
    }}""",
    
    "talisman_drops_only": PREFIXES + """
    SELECT DISTINCT ?itemName WHERE {{
        ?item er:droppedBy ?boss ; rdfs:label ?itemName ; a er:Talisman .
        ?boss rdfs:label ?bossName .
        FILTER(LCASE(?bossName) = LCASE("{name}"))
    }}""",
    
    "remembrance_drop": PREFIXES + """
    SELECT DISTINCT ?remName WHERE {{
        ?rem a er:Remembrance ; er:droppedBy ?boss ; rdfs:label ?remName .
        ?boss rdfs:label ?bossName .
        FILTER(LCASE(?bossName) = LCASE("{name}"))
    }}""",
    
    "who_drops_item": PREFIXES + """
    SELECT DISTINCT ?bossName WHERE {{
        ?item er:droppedBy ?boss ; rdfs:label ?itemName .
        ?boss rdfs:label ?bossName .
        FILTER(LCASE(?itemName) = LCASE("{item_name}"))
    }}""",
    
    "who_drops_weapon_type": PREFIXES + """
    SELECT DISTINCT ?bossName ?weaponName WHERE {{
        ?w a ?type ; er:droppedBy ?boss ; rdfs:label ?weaponName .
        ?boss rdfs:label ?bossName .
        FILTER(CONTAINS(LCASE(STR(?type)), LCASE("{w_type}")))
    }} LIMIT 20""",
    
    "bosses_dropping_runes_gt": PREFIXES + """
    SELECT DISTINCT ?name ?runes WHERE {{
        ?b a er:Boss ; rdfs:label ?name ; er:runesDropped ?runes .
        FILTER(?runes > {value})
    }} ORDER BY DESC(?runes) LIMIT 20""",
    
    "bosses_dropping_bell_bearings": PREFIXES + """
    SELECT DISTINCT ?bossName ?bellName WHERE {{
        ?bell a er:BellBearing ; er:droppedBy ?boss ; rdfs:label ?bellName .
        ?boss rdfs:label ?bossName .
    }} LIMIT 20""",
    
    "bosses_dropping_legendary": PREFIXES + """
    SELECT DISTINCT ?bossName ?itemName WHERE {{
        ?item er:droppedBy ?boss ; rdfs:label ?itemName ; a er:LegendaryItem .
        ?boss rdfs:label ?bossName .
    }} LIMIT 20""",
    
    "remembrance_rewards": PREFIXES + """
    SELECT DISTINCT ?rewardName WHERE {{
        ?boss rdfs:label ?bName .
        FILTER(LCASE(?bName) = LCASE("{name}")) .
        ?rem er:droppedBy ?boss ; er:unlocksReward ?reward .
        ?reward rdfs:label ?rewardName .
    }}""",

    # --- INTENT: boss_location (5 Templates) ---
    
    "boss_exact_loc": PREFIXES + """
    SELECT DISTINCT ?locName WHERE {{
        ?b a er:Boss ; rdfs:label ?name ; er:locatedIn ?loc .
        ?loc rdfs:label ?locName .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}""",
    
    "bosses_in_region_search": PREFIXES + """
    SELECT DISTINCT ?bossName WHERE {{
        ?b a er:Boss ; rdfs:label ?bossName ; er:locatedIn ?loc .
        ?loc rdfs:label ?locName .
        FILTER(CONTAINS(LCASE(?locName), LCASE("{region}")))
    }} LIMIT 20""",
    
    "evergaol_bosses": PREFIXES + """
    SELECT DISTINCT ?bossName WHERE {{
        ?b a er:Boss ; rdfs:label ?bossName ; er:locatedIn ?loc .
        ?loc rdfs:label ?locName .
        FILTER(CONTAINS(LCASE(?locName), "evergaol"))
    }}""",
    
    "dungeon_bosses": PREFIXES + """
    SELECT DISTINCT ?bossName ?dungeonName WHERE {{
        ?b a er:Boss ; rdfs:label ?bossName ; er:locatedIn ?loc .
        ?loc rdfs:label ?dungeonName .
        FILTER(CONTAINS(LCASE(?dungeonName), "catacombs") || CONTAINS(LCASE(?dungeonName), "cave") || CONTAINS(LCASE(?dungeonName), "tunnel"))
    }} LIMIT 20""",
    
    "roaming_bosses": PREFIXES + """
    SELECT DISTINCT ?bossName WHERE {{
        ?b a er:Boss ; rdfs:label ?bossName ; a er:RoamingBoss .
    }} LIMIT 20"""
}