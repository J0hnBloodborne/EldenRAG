# templates/analytics.py

PREFIXES = """
PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

ANALYTIC_TEMPLATES = {
    # --- INTENT: compare_stat_distribution ---

    # 1. Count Weapons by Scaling Grade ("How many weapons have S Dex?")
    "count_scaling": PREFIXES + """
    SELECT (COUNT(?w) AS ?count) WHERE {{
        ?w a er:Weapon ; er:hasMaxStats ?m .
        ?m er:scaling{stat} "{grade}" .
    }}
    """,

    # 2. Count Weapons by Category ("How many Katanas are there?")
    "count_category": PREFIXES + """
    SELECT (COUNT(?w) AS ?count) WHERE {{
        ?w a ?type .
        FILTER(CONTAINS(LCASE(STR(?type)), LCASE("{category}"))) .
    }}
    """,

    # --- INTENT: top_k_by_attribute ---

    # 3. Top HP Bosses ("Bosses with most HP")
    "top_hp_bosses": PREFIXES + """
    SELECT DISTINCT ?name ?hp WHERE {{
        ?b a er:Boss ; rdfs:label ?name ; er:healthPoints ?hp .
    }} ORDER BY DESC(?hp) LIMIT {k}
    """,

    # 4. Top Rune Drops ("Bosses giving most runes")
    "top_rune_bosses": PREFIXES + """
    SELECT DISTINCT ?name ?runes WHERE {{
        ?b a er:Boss ; rdfs:label ?name ; er:runesDropped ?runes .
    }} ORDER BY DESC(?runes) LIMIT {k}
    """
}