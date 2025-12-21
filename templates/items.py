# templates/items.py

PREFIXES = """
PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

ITEM_TEMPLATES = {
    # --- INTENT: item_lookup (10 Templates) ---
    
    # 1. Basic Talisman Info
    "talisman_basic": PREFIXES + """
    SELECT DISTINCT ?effect WHERE {{
        ?t a er:Talisman ; rdfs:label ?name ; er:effect ?effect .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}
    """,
    # 2. Consumable Description
    "consumable_basic": PREFIXES + """
    SELECT DISTINCT ?desc WHERE {{
        ?c a er:Consumable ; rdfs:label ?name ; rdfs:comment ?desc .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}
    """,
    # 3. Crafting Material Sources
    "material_source": PREFIXES + """
    SELECT DISTINCT ?locName ?droppedBy WHERE {{
        ?m a er:CraftingMaterial ; rdfs:label ?name .
        FILTER(LCASE(?name) = LCASE("{name}")) .
        OPTIONAL {{ ?m er:foundIn ?loc . ?loc rdfs:label ?locName }}
        OPTIONAL {{ ?m er:droppedBy ?mob . ?mob rdfs:label ?droppedBy }}
    }}
    """,
    # 4. Key Item Purpose
    "key_item_use": PREFIXES + """
    SELECT DISTINCT ?desc WHERE {{
        ?k a er:KeyItem ; rdfs:label ?name ; rdfs:comment ?desc .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}
    """,
    # 5. Crystal Tear Effect
    "tear_effect": PREFIXES + """
    SELECT DISTINCT ?effect WHERE {{
        ?c a er:CrystalTear ; rdfs:label ?name ; er:effect ?effect .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}
    """,
    # 6. Recipe Lookup (What makes this?)
    "recipe_for_item": PREFIXES + """
    SELECT DISTINCT ?matName ?amount WHERE {{
        ?item rdfs:label ?name ; er:requiresMaterial ?node .
        ?node er:material ?mat ; er:amount ?amount .
        ?mat rdfs:label ?matName .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}
    """,
    # 7. Cookbook Unlock (What does this book teach?)
    "cookbook_unlocks": PREFIXES + """
    SELECT DISTINCT ?recipeName WHERE {{
        ?book a er:Cookbook ; rdfs:label ?name ; er:unlocksRecipe ?recipe .
        ?recipe rdfs:label ?recipeName .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}
    """,
    # 8. Tool Usage (Prattling Pates, etc.)
    "tool_usage": PREFIXES + """
    SELECT DISTINCT ?desc WHERE {{
        ?t a er:Tool ; rdfs:label ?name ; rdfs:comment ?desc .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}
    """,
    # 9. Great Rune Benefits
    "great_rune_effect": PREFIXES + """
    SELECT DISTINCT ?effect WHERE {{
        ?r a er:GreatRune ; rdfs:label ?name ; er:effect ?effect .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}
    """,
    # 10. Bell Bearing Shop
    "bell_bearing_shop": PREFIXES + """
    SELECT DISTINCT ?shopItem WHERE {{
        ?b a er:BellBearing ; rdfs:label ?name ; er:unlocksItem ?item .
        ?item rdfs:label ?shopItem .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}
    """,

    # --- INTENT: item_effects (10 Templates) ---

    # 11. Passive Effect Search ("Items causing Bleed")
    "passive_search": PREFIXES + """
    SELECT DISTINCT ?name ?passive WHERE {{
        ?item er:passiveEffect ?passive ; rdfs:label ?name .
        FILTER(CONTAINS(LCASE(?passive), LCASE("{keyword}")))
    }} LIMIT 20
    """,
    # 12. Talisman Buff Search ("Talismans boosting Stamina")
    "talisman_buff_search": PREFIXES + """
    SELECT DISTINCT ?name ?effect WHERE {{
        ?t a er:Talisman ; rdfs:label ?name ; er:effect ?effect .
        FILTER(CONTAINS(LCASE(?effect), LCASE("{keyword}")))
    }} LIMIT 20
    """,
    # 13. Tear Buff Search ("Tears boosting Fire")
    "tear_buff_search": PREFIXES + """
    SELECT DISTINCT ?name ?effect WHERE {{
        ?t a er:CrystalTear ; rdfs:label ?name ; er:effect ?effect .
        FILTER(CONTAINS(LCASE(?effect), LCASE("{keyword}")))
    }} LIMIT 20
    """,
    # 14. Consumable Buff Search ("Consumables for defense")
    "consumable_buff_search": PREFIXES + """
    SELECT DISTINCT ?name ?desc WHERE {{
        ?c a er:Consumable ; rdfs:label ?name ; rdfs:comment ?desc .
        FILTER(CONTAINS(LCASE(?desc), LCASE("{keyword}")))
    }} LIMIT 20
    """,
    # 15. Negative Effect Search ("Items that increase damage taken")
    "debuff_search": PREFIXES + """
    SELECT DISTINCT ?name ?effect WHERE {{
        ?item er:effect ?effect ; rdfs:label ?name .
        FILTER(CONTAINS(LCASE(?effect), "increases damage taken") || CONTAINS(LCASE(?effect), "reduces"))
        FILTER(CONTAINS(LCASE(?effect), LCASE("{keyword}"))) 
    }} LIMIT 20
    """,
    # 16. Multi-Effect Search ("Items boosting Int AND Faith")
    "multi_buff_search": PREFIXES + """
    SELECT DISTINCT ?name ?effect WHERE {{
        ?item er:effect ?effect ; rdfs:label ?name .
        FILTER(CONTAINS(LCASE(?effect), LCASE("{kw1}")) && CONTAINS(LCASE(?effect), LCASE("{kw2}")))
    }} LIMIT 20
    """,
    # 17. Status Cure Search ("Items that cure Poison")
    "cure_search": PREFIXES + """
    SELECT DISTINCT ?name ?desc WHERE {{
        ?c a er:Consumable ; rdfs:label ?name ; rdfs:comment ?desc .
        FILTER(CONTAINS(LCASE(?desc), "alleviates") || CONTAINS(LCASE(?desc), "cures"))
        FILTER(CONTAINS(LCASE(?desc), LCASE("{status}")))
    }} LIMIT 20
    """,
    # 18. FP Cost Effect ("Items reducing FP cost")
    "fp_cost_effect": PREFIXES + """
    SELECT DISTINCT ?name ?effect WHERE {{
        ?item er:effect ?effect ; rdfs:label ?name .
        FILTER(CONTAINS(LCASE(?effect), "fp") && CONTAINS(LCASE(?effect), "consum"))
    }} LIMIT 20
    """,
    # 19. Rune Gain Effect ("Items boosting rune acquisition")
    "rune_gain_effect": PREFIXES + """
    SELECT DISTINCT ?name ?effect WHERE {{
        ?item er:effect ?effect ; rdfs:label ?name .
        FILTER(CONTAINS(LCASE(?effect), "rune"))
    }} LIMIT 20
    """,
    # 20. Discovery Effect ("Items boosting discovery")
    "discovery_effect": PREFIXES + """
    SELECT DISTINCT ?name ?effect WHERE {{
        ?item er:effect ?effect ; rdfs:label ?name .
        FILTER(CONTAINS(LCASE(?effect), "discovery"))
    }} LIMIT 20
    """,

    # --- INTENT: skill_lookup (10 Templates) ---

    # 21. Ash of War Info
    "aow_info": PREFIXES + """
    SELECT DISTINCT ?desc ?affinity WHERE {{
        ?a a er:AshOfWar ; rdfs:label ?name ; rdfs:comment ?desc .
        FILTER(LCASE(?name) = LCASE("{name}")) .
        OPTIONAL {{ ?a er:grantsAffinity ?affinity }}
    }}
    """,
    # 22. Weapon Specific Skill
    "weapon_default_skill": PREFIXES + """
    SELECT DISTINCT ?skillName ?desc WHERE {{
        ?w a er:Weapon ; rdfs:label ?wName ; er:hasSkill ?s .
        ?s rdfs:label ?skillName ; rdfs:comment ?desc .
        FILTER(LCASE(?wName) = LCASE("{name}"))
    }}
    """,
    # 23. Skill Search by Keyword
    "skill_search": PREFIXES + """
    SELECT DISTINCT ?name ?desc WHERE {{
        ?s a er:Skill ; rdfs:label ?name ; rdfs:comment ?desc .
        FILTER(CONTAINS(LCASE(?desc), LCASE("{keyword}")))
    }} LIMIT 20
    """,
    # 24. FP Cost of Skill (If data exists)
    "skill_fp_cost": PREFIXES + """
    SELECT DISTINCT ?name ?fp WHERE {{
        ?s a er:Skill ; rdfs:label ?name ; er:fpCost ?fp .
        FILTER(LCASE(?name) = LCASE("{name}"))
    }}
    """,
    # 25. AoW by Affinity ("Ashes that grant Blood")
    "aow_by_affinity": PREFIXES + """
    SELECT DISTINCT ?name WHERE {{
        ?a a er:AshOfWar ; rdfs:label ?name ; er:grantsAffinity ?aff .
        FILTER(CONTAINS(LCASE(?aff), LCASE("{affinity}")))
    }} LIMIT 20
    """,
    # 26. Unique Skills ("Skills only on one weapon")
    "unique_skills": PREFIXES + """
    SELECT DISTINCT ?skillName ?weaponName WHERE {{
        ?w a er:Weapon ; rdfs:label ?weaponName ; er:hasSkill ?s .
        ?s rdfs:label ?skillName ; a er:UniqueSkill .
    }} LIMIT 20
    """,
    # 27. Roar Skills
    "roar_skills": PREFIXES + """
    SELECT DISTINCT ?name ?desc WHERE {{
        ?s a er:Skill ; rdfs:label ?name ; rdfs:comment ?desc .
        FILTER(CONTAINS(LCASE(?name), "roar") || CONTAINS(LCASE(?name), "cry"))
    }} LIMIT 20
    """,
    # 28. Slash Skills
    "slash_skills": PREFIXES + """
    SELECT DISTINCT ?name ?desc WHERE {{
        ?s a er:Skill ; rdfs:label ?name ; rdfs:comment ?desc .
        FILTER(CONTAINS(LCASE(?name), "slash") || CONTAINS(LCASE(?name), "cut"))
    }} LIMIT 20
    """,
    # 29. Magic Skills
    "magic_skills": PREFIXES + """
    SELECT DISTINCT ?name ?desc WHERE {{
        ?s a er:Skill ; rdfs:label ?name ; rdfs:comment ?desc .
        FILTER(CONTAINS(LCASE(?desc), "glintstone") || CONTAINS(LCASE(?desc), "magic"))
    }} LIMIT 20
    """,
    # 30. Stance Skills
    "stance_skills": PREFIXES + """
    SELECT DISTINCT ?name ?desc WHERE {{
        ?s a er:Skill ; rdfs:label ?name ; rdfs:comment ?desc .
        FILTER(CONTAINS(LCASE(?name), "stance"))
    }} LIMIT 20
    """
}