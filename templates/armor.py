# templates/armor.py

PREFIXES = """
PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

ARMOR_TEMPLATES = {
    # --- INTENT: armor_lookup ---
    
    # 1. Basic Stats ("Stats for Radahn's Armor")
    "basic_lookup": PREFIXES + """
    SELECT DISTINCT ?prop ?val WHERE {{
        ?a a er:Armor ; rdfs:label ?name .
        FILTER(LCASE(?name) = LCASE("{name}")) .
        ?a ?p ?val .
        BIND(STRAFTER(STR(?p), "http://www.semanticweb.org/fall2025/eldenring/") AS ?prop)
        FILTER(?prop != "")
    }}
    """,

    # 2. Get Set Pieces ("What is in the Cleanrot Set?")
    # Heuristic: Name matching or explicit set link if available
    "set_lookup_by_name": PREFIXES + """
    SELECT DISTINCT ?pieceName ?type WHERE {{
        ?piece a er:Armor ; rdfs:label ?pieceName ; a ?type .
        FILTER(CONTAINS(LCASE(?pieceName), LCASE("{set_name}"))) .
        FILTER(?type != er:Armor) # Get specific type like Helm/Chest
    }}
    """,

    # --- INTENT: armor_by_defense ---

    # 3. High Physical Defense ("Best physical armor")
    "high_physical": PREFIXES + """
    SELECT DISTINCT ?name ?val ?weight WHERE {{
        ?a a er:Armor ; rdfs:label ?name ; er:negatesPhysical ?val ; er:weight ?weight .
    }} ORDER BY DESC(?val) LIMIT 20
    """,

    # 4. High Magic Defense ("Armor good against Magic")
    "high_magic": PREFIXES + """
    SELECT DISTINCT ?name ?val ?weight WHERE {{
        ?a a er:Armor ; rdfs:label ?name ; er:negatesMagic ?val ; er:weight ?weight .
    }} ORDER BY DESC(?val) LIMIT 20
    """,

    # 5. High Fire Defense
    "high_fire": PREFIXES + """
    SELECT DISTINCT ?name ?val ?weight WHERE {{
        ?a a er:Armor ; rdfs:label ?name ; er:negatesFire ?val ; er:weight ?weight .
    }} ORDER BY DESC(?val) LIMIT 20
    """,

    # 6. High Lightning Defense
    "high_lightning": PREFIXES + """
    SELECT DISTINCT ?name ?val ?weight WHERE {{
        ?a a er:Armor ; rdfs:label ?name ; er:negatesLightning ?val ; er:weight ?weight .
    }} ORDER BY DESC(?val) LIMIT 20
    """,

    # 7. High Holy Defense
    "high_holy": PREFIXES + """
    SELECT DISTINCT ?name ?val ?weight WHERE {{
        ?a a er:Armor ; rdfs:label ?name ; er:negatesHoly ?val ; er:weight ?weight .
    }} ORDER BY DESC(?val) LIMIT 20
    """,

    # 8. High Poise ("Armor with > 50 Poise")
    "poise_threshold": PREFIXES + """
    SELECT DISTINCT ?name ?poise ?weight WHERE {{
        ?a a er:Armor ; rdfs:label ?name ; er:poise ?poise ; er:weight ?weight .
        FILTER(?poise >= {value})
    }} ORDER BY ASC(?weight) LIMIT 20
    """,

    # --- INTENT: armor_by_weight ---

    # 9. Light Armor ("Armor lighter than 5.0")
    "weight_lt": PREFIXES + """
    SELECT DISTINCT ?name ?weight ?phys WHERE {{
        ?a a er:Armor ; rdfs:label ?name ; er:weight ?weight ; er:negatesPhysical ?phys .
        FILTER(?weight < {value})
    }} ORDER BY DESC(?phys) LIMIT 20
    """,

    # 10. Heavy Armor ("Armor heavier than 20.0")
    "weight_gt": PREFIXES + """
    SELECT DISTINCT ?name ?weight ?phys WHERE {{
        ?a a er:Armor ; rdfs:label ?name ; er:weight ?weight ; er:negatesPhysical ?phys .
        FILTER(?weight > {value})
    }} ORDER BY DESC(?phys) LIMIT 20
    """,

    # --- INTENT: armor_comparison ---

    # 11. Compare 2 Armors ("Radahn vs Malenia Armor")
    "compare_two": PREFIXES + """
    SELECT DISTINCT ?name ?weight ?phys ?magic ?fire ?light ?holy ?poise WHERE {{
        ?a a er:Armor ; rdfs:label ?name .
        FILTER(LCASE(?name) IN (LCASE("{name1}"), LCASE("{name2}"))) .
        OPTIONAL {{ ?a er:weight ?weight }}
        OPTIONAL {{ ?a er:negatesPhysical ?phys }}
        OPTIONAL {{ ?a er:negatesMagic ?magic }}
        OPTIONAL {{ ?a er:negatesFire ?fire }}
        OPTIONAL {{ ?a er:negatesLightning ?light }}
        OPTIONAL {{ ?a er:negatesHoly ?holy }}
        OPTIONAL {{ ?a er:poise ?poise }}
    }}
    """
}