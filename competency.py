import time
from rdflib import Graph, Namespace

print("Loading Fast Graph...")
start = time.time()
g = Graph()
# LOAD THE FAST FILE
g.parse("elden_ring_fast.nt", format="nt") 
print(f"Loaded {len(g)} triples in {time.time() - start:.4f} seconds.")

# Queries (Same as before)
queries = {
    "1. INT Weapons": """
        PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX attribute: <http://www.semanticweb.org/fall2025/eldenring/Attribute/>
        SELECT DISTINCT ?weaponName ?weight WHERE {
            ?w a er:Weapon ; rdfs:label ?weaponName ; er:hasWeight ?weight .
            ?u er:isUpgradeOf ?w ; er:scalesWith attribute:Int .
            FILTER(STRENDS(STR(?u), "Standard")) FILTER (?weight < 3.0)
        } ORDER BY ?weight LIMIT 10
    """,
    "2. Remembrances": """
        PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?bossName ?remName WHERE {
            ?rem a er:Remembrance ; rdfs:label ?remName ; er:droppedBy ?boss .
            ?boss rdfs:label ?bossName .
        } ORDER BY ?bossName LIMIT 10
    """,
    "3. Location Counts": """
        PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?locName (COUNT(?boss) as ?bossCount) WHERE {
            ?loc a er:Location ; rdfs:label ?locName ; er:hasBoss ?boss .
        } GROUP BY ?locName ORDER BY DESC(?bossCount) LIMIT 5
    """,
    "4. Cookbooks": """
        PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?bookName ?itemName WHERE {
            ?book a er:Cookbook ; rdfs:label ?bookName ; er:unlocksRecipeFor ?item .
            ?item rdfs:label ?itemName .
        } LIMIT 5
    """,
    "5. Whetblades": """
        PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?bladeName ?affinityName WHERE {
            ?w a er:Whetblade ; rdfs:label ?bladeName ; er:unlocksAffinity ?a .
            ?a rdfs:label ?affinityName .
        } LIMIT 5
    """
}

for title, q in queries.items():
    print(f"\n{title}")
    try:
        results = g.query(q)
        if len(results) == 0: print("No results.")
        else:
            for row in results:
                print(f"{', '.join([str(i).split('/')[-1] for i in row])}")
    except Exception as e: print(f"Error: {e}")