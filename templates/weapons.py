# templates/weapons.py

PREFIXES = """
PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

# Helper to sort grades correctly (S is best, E is worst)
# Note: We use double braces for SPARQL syntax that shouldn't be touched by Python format()
ORDER_BY_GRADE = """
ORDER BY ASC(
  CASE ?val
    WHEN "S" THEN 1
    WHEN "A" THEN 2
    WHEN "B" THEN 3
    WHEN "C" THEN 4
    WHEN "D" THEN 5
    WHEN "E" THEN 6
    ELSE 7
  END
)
"""

SCALING_TEMPLATES = {
    # 1. Exact Grade Match
    "exact_grade": PREFIXES + """
    SELECT DISTINCT ?name ?val ?upgradePath WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:hasMaxStats ?m .
        ?m er:scaling{stat} ?val .
        ?m er:upgradePath ?upgradePath .
        FILTER(?val = "{grade}")
    }} LIMIT 20
    """,

    # 2. Minimum Threshold
    # We pre-format the order clause so it's part of the static string
    "grade_threshold": PREFIXES + """
    SELECT DISTINCT ?name ?val ?upgradePath WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:hasMaxStats ?m .
        ?m er:scaling{stat} ?val .
        ?m er:upgradePath ?upgradePath .
        FILTER(?val IN ({grade_list}))
    }} """ + ORDER_BY_GRADE + """ LIMIT 20
    """,

    # 3. Best in Slot
    "best_in_slot": PREFIXES + """
    SELECT DISTINCT ?name ?val ?upgradePath WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:hasMaxStats ?m .
        ?m er:scaling{stat} ?val .
        ?m er:upgradePath ?upgradePath .
        FILTER(?val != "-")
    }} """ + ORDER_BY_GRADE + """ LIMIT 10
    """,

    # 4. Hybrid AND
    "hybrid_and": PREFIXES + """
    SELECT DISTINCT ?name ?val1 ?val2 ?upgradePath WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:hasMaxStats ?m .
        ?m er:scaling{stat1} ?val1 ; er:scaling{stat2} ?val2 .
        ?m er:upgradePath ?upgradePath .
        FILTER(?val1 != "-" && ?val2 != "-")
    }} LIMIT 20
    """,

    # 5. Hybrid OR
    "hybrid_or": PREFIXES + """
    SELECT DISTINCT ?name ?val1 ?val2 ?upgradePath WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:hasMaxStats ?m .
        ?m er:scaling{stat1} ?val1 ; er:scaling{stat2} ?val2 .
        ?m er:upgradePath ?upgradePath .
        FILTER(?val1 != "-" || ?val2 != "-")
    }} LIMIT 20
    """,

    # 6. Quality Build
    "quality_build": PREFIXES + """
    SELECT DISTINCT ?name ?strVal ?dexVal ?upgradePath WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:hasMaxStats ?m .
        ?m er:scalingStrength ?strVal ; er:scalingDexterity ?dexVal .
        ?m er:upgradePath ?upgradePath .
        FILTER(?strVal IN ("S","A","B","C") && ?dexVal IN ("S","A","B","C"))
    }} LIMIT 20
    """,

    # 7. Pure Stat Scaling
    "pure_scaling": PREFIXES + """
    SELECT DISTINCT ?name ?val ?upgradePath WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:hasMaxStats ?m .
        ?m er:scaling{stat} ?val .
        ?m er:upgradePath ?upgradePath .
        ?m er:scalingStrength ?s ; er:scalingDexterity ?d ; er:scalingIntelligence ?i ; er:scalingFaith ?f ; er:scalingArcane ?a .
        
        FILTER(?val != "-")
        FILTER("{stat}" = "Strength" || ?s = "-")
        FILTER("{stat}" = "Dexterity" || ?d = "-")
        FILTER("{stat}" = "Intelligence" || ?i = "-")
        FILTER("{stat}" = "Faith" || ?f = "-")
        FILTER("{stat}" = "Arcane" || ?a = "-")
    }} LIMIT 20
    """,

    # 8. Negative Constraint
    "no_scaling": PREFIXES + """
    SELECT DISTINCT ?name ?upgradePath WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:hasMaxStats ?m .
        ?m er:scaling{stat} ?val .
        ?m er:upgradePath ?upgradePath .
        FILTER(?val = "-")
    }} LIMIT 20
    """,

    # 9. Scaling + Weapon Type
    "scaling_with_type": PREFIXES + """
    SELECT DISTINCT ?name ?val ?upgradePath WHERE {{
        ?w a ?type ; rdfs:label ?name ; er:hasMaxStats ?m .
        FILTER(CONTAINS(LCASE(STR(?type)), LCASE("{w_type}"))) .
        ?m er:scaling{stat} ?val .
        ?m er:upgradePath ?upgradePath .
        FILTER(?val IN ({grade_list}))
    }} LIMIT 20
    """,

    # 10. Scaling + Infusion
    "scaling_with_infusion": PREFIXES + """
    SELECT DISTINCT ?name ?val ?path WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:hasMaxStats ?m .
        ?m er:scaling{stat} ?val .
        ?m er:upgradePath ?path .
        FILTER(CONTAINS(LCASE(?path), LCASE("{infusion}"))) .
        FILTER(?val IN ({grade_list}))
    }} LIMIT 20
    """,

    # 11. Scaling + Passive Effect
    "scaling_with_effect": PREFIXES + """
    SELECT DISTINCT ?name ?val ?effect ?upgradePath WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:passiveEffect ?effect ; er:hasMaxStats ?m .
        FILTER(CONTAINS(LCASE(?effect), LCASE("{effect}"))) .
        ?m er:scaling{stat} ?val .
        ?m er:upgradePath ?upgradePath .
        FILTER(?val IN ({grade_list}))
    }} LIMIT 20
    """,

    # 12. Scaling + Damage Type
    "scaling_with_damage": PREFIXES + """
    SELECT DISTINCT ?name ?val ?dmg ?upgradePath WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:damageType ?dmg ; er:hasMaxStats ?m .
        FILTER(CONTAINS(LCASE(?dmg), LCASE("{dmg_type}"))) .
        ?m er:scaling{stat} ?val .
        ?m er:upgradePath ?upgradePath .
        FILTER(?val IN ({grade_list}))
    }} LIMIT 20
    """,
    
    # 13. Scaling + Skill
    "scaling_with_skill": PREFIXES + """
    SELECT DISTINCT ?name ?val ?skill ?upgradePath WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:hasSkill ?sURI ; er:hasMaxStats ?m .
        ?sURI rdfs:label ?skill .
        FILTER(CONTAINS(LCASE(?skill), LCASE("{skill}"))) .
        ?m er:scaling{stat} ?val .
        ?m er:upgradePath ?upgradePath .
        FILTER(?val IN ({grade_list}))
    }} LIMIT 20
    """,

    # 14. Top K Analysis
    "top_k_stat": PREFIXES + """
    SELECT DISTINCT ?name ?val ?upgradePath WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:hasMaxStats ?m .
        ?m er:scaling{stat} ?val .
        ?m er:upgradePath ?upgradePath .
        FILTER(?val != "-")
    }} """ + ORDER_BY_GRADE + """ LIMIT {k}
    """,

    # 15. Scaling Distribution
    "scaling_distribution": PREFIXES + """
    SELECT (COUNT(?w) as ?count) WHERE {{
        ?w a er:Weapon ; er:hasMaxStats ?m .
        ?m er:scaling{stat} "{grade}" .
    }}
    """,
    
    # 16. Scaling for Specific Weapon
    "lookup_scaling": PREFIXES + """
    SELECT DISTINCT ?val ?path WHERE {{
        ?w rdfs:label ?name .
        FILTER(LCASE(?name) = LCASE("{name}")) .
        ?w er:hasMaxStats ?m .
        ?m er:scaling{stat} ?val .
        ?m er:upgradePath ?path .
    }}
    """,

    # 17. Scaling + Weight
    "scaling_with_weight": PREFIXES + """
    SELECT DISTINCT ?name ?val ?weight ?upgradePath WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:weight ?weight ; er:hasMaxStats ?m .
        ?m er:scaling{stat} ?val .
        ?m er:upgradePath ?upgradePath .
        FILTER(?val IN ({grade_list})) .
        FILTER(?weight {operator} {weight_val})
    }} LIMIT 20
    """,

    # 18. Triple Stat Scaling
    "triple_stat_scaling": PREFIXES + """
    SELECT DISTINCT ?name ?val1 ?val2 ?val3 ?upgradePath WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:hasMaxStats ?m .
        ?m er:scaling{stat1} ?val1 ; er:scaling{stat2} ?val2 ; er:scaling{stat3} ?val3 .
        ?m er:upgradePath ?upgradePath .
        FILTER(?val1 != "-" && ?val2 != "-" && ?val3 != "-")
    }} LIMIT 20
    """
}

# --- INTENT: weapon_by_requirements ---
REQUIREMENT_TEMPLATES = {
    "simple_req": PREFIXES + """
    SELECT DISTINCT ?name ?req WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:requires{stat} ?req .
        FILTER(?req {operator} {value})
    }} LIMIT 20
    """,

    "dual_req": PREFIXES + """
    SELECT DISTINCT ?name ?req1 ?req2 WHERE {{
        ?w a er:Weapon ; rdfs:label ?name .
        ?w er:requires{stat1} ?req1 .
        ?w er:requires{stat2} ?req2 .
        FILTER(?req1 {op1} {val1} && ?req2 {op2} {val2})
    }} LIMIT 20
    """,

    "req_with_type": PREFIXES + """
    SELECT DISTINCT ?name ?req WHERE {{
        ?w a ?type ; rdfs:label ?name ; er:requires{stat} ?req .
        FILTER(CONTAINS(LCASE(STR(?type)), LCASE("{w_type}"))) .
        FILTER(?req {operator} {value})
    }} LIMIT 20
    """,

    "low_reqs": PREFIXES + """
    SELECT DISTINCT ?name ?req WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:requires{stat} ?req .
        FILTER(?req <= {value})
    }} ORDER BY ASC(?req) LIMIT 20
    """,

    "highest_req": PREFIXES + """
    SELECT DISTINCT ?name ?req WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:requires{stat} ?req .
    }} ORDER BY DESC(?req) LIMIT 10
    """,
    
    "req_with_effect": PREFIXES + """
    SELECT DISTINCT ?name ?req ?effect WHERE {{
        ?w a er:Weapon ; rdfs:label ?name ; er:requires{stat} ?req ; er:passiveEffect ?effect .
        FILTER(CONTAINS(LCASE(?effect), LCASE("{effect}"))) .
        FILTER(?req {operator} {value})
    }} LIMIT 20
    """
}

# --- INTENT: weapon_lookup ---
LOOKUP_TEMPLATES = {
    "full_info": PREFIXES + """
    SELECT DISTINCT ?p ?o WHERE {{
        ?w rdfs:label ?name .
        FILTER(LCASE(?name) = LCASE("{name}")) .
        ?w ?p ?o .
        FILTER(?p != er:hasMaxStats)
    }}
    """,

    "max_stats_all": PREFIXES + """
    SELECT DISTINCT ?p ?o ?path WHERE {{
        ?w rdfs:label ?name .
        FILTER(LCASE(?name) = LCASE("{name}")) .
        ?w er:hasMaxStats ?m .
        ?m er:upgradePath ?path .
        ?m ?p ?o .
    }}
    """,

    "description": PREFIXES + """
    SELECT DISTINCT ?desc WHERE {{
        ?w rdfs:label ?name .
        FILTER(LCASE(?name) = LCASE("{name}")) .
        OPTIONAL {{ ?w rdfs:comment ?desc }}
        OPTIONAL {{ ?w schema:description ?desc }}
    }}
    """,

    "drop_location": PREFIXES + """
    SELECT DISTINCT ?locationName ?bossName WHERE {{
        ?w rdfs:label ?name .
        FILTER(LCASE(?name) = LCASE("{name}")) .
        OPTIONAL {{ ?w er:droppedBy ?boss . ?boss rdfs:label ?bossName }}
        OPTIONAL {{ ?w er:foundIn ?loc . ?loc rdfs:label ?locationName }}
        OPTIONAL {{ ?w er:locatedIn ?loc2 . ?loc2 rdfs:label ?locationName }}
    }}
    """,

    "weapon_skill": PREFIXES + """
    SELECT DISTINCT ?skillName WHERE {{
        ?w rdfs:label ?name .
        FILTER(LCASE(?name) = LCASE("{name}")) .
        ?w er:hasSkill ?s .
        ?s rdfs:label ?skillName .
    }}
    """
}