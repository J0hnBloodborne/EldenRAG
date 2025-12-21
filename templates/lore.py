# templates/lore.py

PREFIXES = """
PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

LORE_TEMPLATES = {
    # --- INTENT: mentions_trace (10 Templates) ---
    
    # 1. Who mentions X?
    "mentions_in_desc": PREFIXES + """
    SELECT DISTINCT ?sourceName WHERE {{
        ?source er:mentions ?target ; rdfs:label ?sourceName .
        ?target rdfs:label ?targetName .
        FILTER(LCASE(?targetName) = LCASE("{entity}"))
    }} LIMIT 20""",
    
    # 2. Who does X mention?
    "x_mentions_who": PREFIXES + """
    SELECT DISTINCT ?targetName WHERE {{
        ?source er:mentions ?target ; rdfs:label ?sourceName .
        ?target rdfs:label ?targetName .
        FILTER(LCASE(?sourceName) = LCASE("{entity}"))
    }} LIMIT 20""",
    
    # 3. Weapons mentioning X
    "weapons_mentioning": PREFIXES + """
    SELECT DISTINCT ?wName WHERE {{
        ?w a er:Weapon ; rdfs:label ?wName ; er:mentions ?target .
        ?target rdfs:label ?tName .
        FILTER(LCASE(?tName) = LCASE("{entity}"))
    }} LIMIT 20""",
    
    # 4. Armor mentioning X
    "armor_mentioning": PREFIXES + """
    SELECT DISTINCT ?aName WHERE {{
        ?a a er:Armor ; rdfs:label ?aName ; er:mentions ?target .
        ?target rdfs:label ?tName .
        FILTER(LCASE(?tName) = LCASE("{entity}"))
    }} LIMIT 20""",
    
    # 5. Talismans mentioning X
    "talisman_mentioning": PREFIXES + """
    SELECT DISTINCT ?tName WHERE {{
        ?t a er:Talisman ; rdfs:label ?tName ; er:mentions ?target .
        ?target rdfs:label ?tName .
        FILTER(LCASE(?tName) = LCASE("{entity}"))
    }} LIMIT 20""",
    
    # 6. Spells mentioning X
    "spells_mentioning": PREFIXES + """
    SELECT DISTINCT ?sName WHERE {{
        { ?s a er:Sorcery } UNION { ?s a er:Incantation } .
        ?s rdfs:label ?sName ; er:mentions ?target .
        ?target rdfs:label ?tName .
        FILTER(LCASE(?tName) = LCASE("{entity}"))
    }} LIMIT 20""",
    
    # 7. Mentions of "God"
    "god_mentions": PREFIXES + """
    SELECT DISTINCT ?name ?desc WHERE {{
        ?s rdfs:label ?name ; rdfs:comment ?desc .
        FILTER(CONTAINS(LCASE(?desc), "outer god") || CONTAINS(LCASE(?desc), "greater will"))
    }} LIMIT 20""",
    
    # 8. Mentions of "Stars"
    "star_mentions": PREFIXES + """
    SELECT DISTINCT ?name ?desc WHERE {{
        ?s rdfs:label ?name ; rdfs:comment ?desc .
        FILTER(CONTAINS(LCASE(?desc), "primeval current") || CONTAINS(LCASE(?desc), "stars"))
    }} LIMIT 20""",
    
    # 9. Mutual Mentions (A mentions B AND B mentions A)
    "mutual_mentions": PREFIXES + """
    SELECT DISTINCT ?name1 ?name2 WHERE {{
        ?e1 rdfs:label ?name1 ; er:mentions ?e2 .
        ?e2 rdfs:label ?name2 ; er:mentions ?e1 .
        FILTER(?name1 < ?name2) # Dedupe pairs
    }} LIMIT 10""",
    
    # 10. Self-Reference (Items mentioning their owner)
    "owner_mentions": PREFIXES + """
    SELECT DISTINCT ?itemName ?ownerName WHERE {{
        ?item rdfs:label ?itemName ; er:mentions ?owner .
        ?owner rdfs:label ?ownerName .
        FILTER(CONTAINS(LCASE(?itemName), LCASE(?ownerName)))
    }} LIMIT 20""",

    # --- INTENT: shared_references (5 Templates) ---
    
    # 11. The "Link" between two entities
    "shared_link": PREFIXES + """
    SELECT DISTINCT ?connectorName WHERE {{
        ?conn er:mentions ?e1 ; er:mentions ?e2 ; rdfs:label ?connectorName .
        ?e1 rdfs:label ?n1 . ?e2 rdfs:label ?n2 .
        FILTER(LCASE(?n1) = LCASE("{entity1}") && LCASE(?n2) = LCASE("{entity2}"))
    }}""",
    
    # 12. Items connecting a Faction
    "faction_cluster": PREFIXES + """
    SELECT DISTINCT ?itemName WHERE {{
        ?item rdfs:label ?itemName ; er:mentions ?entity .
        ?entity rdfs:label ?eName .
        FILTER(CONTAINS(LCASE(?eName), LCASE("{faction}"))) # e.g. "Carian"
    }} LIMIT 20""",
    
    # 13. Boss-Item Connection
    "boss_item_link": PREFIXES + """
    SELECT DISTINCT ?itemName WHERE {{
        ?item rdfs:label ?itemName ; er:droppedBy ?boss ; er:mentions ?boss .
        ?boss rdfs:label ?bName .
        FILTER(LCASE(?bName) = LCASE("{name}"))
    }}""",
    
    # 14. Location-Lore Link
    "location_lore": PREFIXES + """
    SELECT DISTINCT ?itemName WHERE {{
        ?item rdfs:label ?itemName ; er:foundIn ?loc ; er:mentions ?loc .
        ?loc rdfs:label ?lName .
        FILTER(LCASE(?lName) = LCASE("{location}"))
    }}""",
    
    # 15. The "Three Sisters" (Ranni, Rykard, Radahn)
    "sibling_check": PREFIXES + """
    SELECT DISTINCT ?item WHERE {{
        ?i rdfs:label ?item ; er:mentions ?e1 ; er:mentions ?e2 .
        ?e1 rdfs:label ?n1 . ?e2 rdfs:label ?n2 .
        FILTER(LCASE(?n1) = "ranni" && LCASE(?n2) = "radahn")
    }}"""
}