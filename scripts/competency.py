import time
from rdflib import Graph, Namespace

# --- CONFIGURATION ---
GRAPH_FILE = "rdf/elden_ring_optimized.ttl"
ER = Namespace("http://www.semanticweb.org/fall2025/eldenring/")

def main():
    print(f"--- 1. LOADING KNOWLEDGE GRAPH: {GRAPH_FILE} ---")
    g = Graph()
    start_time = time.time()
    g.parse(GRAPH_FILE, format="turtle")
    print(f"   [Loaded] {len(g)} triples in {time.time() - start_time:.2f} seconds.\n")

    queries = [
        # --- LEVEL 1: BASIC RETRIEVAL ---
        {
            "name": "1. Simple Lookup (Who is Malenia?)",
            "desc": "Retrieves the label and description of a specific entity.",
            "sparql": """
                PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                
                SELECT ?label ?desc WHERE {
                    er:MaleniaBladeOfMiquella rdfs:label ?label ;
                                              rdfs:comment ?desc .
                }
            """
        },
        {
            "name": "2. Stat Retrieval (The Shadow Node)",
            "desc": "Navigates from a Weapon to its _MaxStats node to find attack power.",
            "sparql": """
                PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
                
                SELECT ?weapon ?phy ?mag WHERE {
                    ?weapon er:hasMaxStats ?stats .
                    ?stats er:attackPhysical ?phy .
                    OPTIONAL { ?stats er:attackMagic ?mag }
                    FILTER (?weapon = er:Moonveil)
                }
            """
        },
        
        # --- LEVEL 2: INFERENCE & INVERSES ---
        {
            "name": "3. Inverse Logic (Who drops this?)",
            "desc": "Tests if 'droppedBy' was inferred from 'drops' (Using Rykard as a clean test case).",
            "sparql": """
                PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

                SELECT ?bossName WHERE {
                    er:RemembranceOfTheBlasphemous er:droppedBy ?boss .
                    ?boss rdfs:label ?bossName .
                }
            """
        },
        {
            "name": "4. Semantic Linking (Lore Scanner)",
            "desc": "Finds items that textually mention 'Miquella'.",
            "sparql": """
                PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

                SELECT ?itemLabel WHERE {
                    ?item er:mentions ?target .
                    ?target rdfs:label "Miquella" . 
                    ?item rdfs:label ?itemLabel .
                } LIMIT 5
            """
        },

        # --- LEVEL 3: TRANSITIVITY & HIERARCHY ---
        {
            "name": "5. Transitive Geography (What is in Caelid?)",
            "desc": "Finds entities located in Caelid OR any sub-location of Caelid.",
            "sparql": """
                PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

                SELECT ?entityName ?locationName WHERE {
                    ?entity er:locatedIn+ er:Caelid .
                    ?entity rdfs:label ?entityName .
                    ?entity er:locatedIn ?directLoc .
                    ?directLoc rdfs:label ?locationName .
                } LIMIT 5
            """
        },
        {
            "name": "6. Class Hierarchy (Polymorphism)",
            "desc": "Finds 'Great Runes' by querying for the parent class 'Item'.",
            "sparql": """
                PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

                SELECT ?name WHERE {
                    ?x a er:GreatRune .
                    ?x a er:Item .
                    ?x rdfs:label ?name .
                } LIMIT 5
            """
        },

        # --- LEVEL 4: COMPLEX FILTERING ---
        {
            "name": "7. The 'Int Build' Query",
            "desc": "Finds weapons with 'S' Intelligence scaling.",
            "sparql": """
                PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

                SELECT ?weaponName ?scaling WHERE {
                    ?w er:hasMaxStats ?stats ;
                       rdfs:label ?weaponName .
                    ?stats er:scalingIntelligence ?scaling .
                    FILTER (?scaling = "S")
                }
            """
        },
        {
            "name": "8. Status Effect Search",
            "desc": "Finds weapons that cause Bleed (Hemorrhage).",
            "sparql": """
                PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

                SELECT ?weaponName WHERE {
                    ?w er:causesEffect er:Hemorrhage ;
                       rdfs:label ?weaponName .
                } LIMIT 5
            """
        },

        # --- LEVEL 5: MULTI-HOP REASONING ---
        {
            "name": "9. Pathfinding (Boss -> Drop -> Stats)",
            "desc": "Find the Physical Damage of the weapon dropped by the Boss of 'Castle Sol'.",
            "sparql": """
                PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

                SELECT ?bossName ?weaponName ?physAtk WHERE {
                    ?boss er:locatedIn er:CastleSol ;
                          rdfs:label ?bossName ;
                          er:drops ?weapon .
                    
                    ?weapon a er:Weapon ;
                            rdfs:label ?weaponName ;
                            er:hasMaxStats ?stats .
                    
                    ?stats er:attackPhysical ?physAtk .
                }
            """
        },
        {
            "name": "10. The 'Scholar' Query (Linked Data)",
            "desc": "Finds items mentioning an Entity that has a Wikidata Link.",
            "sparql": """
                PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
                PREFIX owl: <http://www.w3.org/2002/07/owl#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

                SELECT ?itemLabel ?entityLabel ?wikiURI WHERE {
                    ?item er:mentions ?entity .
                    ?entity owl:sameAs ?wikiURI ;
                            rdfs:label ?entityLabel .
                    ?item rdfs:label ?itemLabel .
                } LIMIT 5
            """
        }
    ]

    print(f"--- 2. EXECUTING {len(queries)} COMPETENCY QUERIES ---\n")
    
    for i, q in enumerate(queries):
        print(f"Q{i+1}: {q['name']}")
        print(f"   [{q['desc']}]")
        
        try:
            results = g.query(q['sparql'])
            count = 0
            for row in results:
                # Clean formatting for display
                clean_row = []
                for val in row:
                    s_val = str(val)
                    if "http" in s_val and "#" in s_val:
                        clean_row.append(s_val.split("#")[-1])
                    elif "http" in s_val and "/" in s_val:
                        clean_row.append(s_val.split("/")[-1])
                    else:
                        clean_row.append(s_val)
                print(f"   -> {clean_row}")
                count += 1
            if count == 0:
                print("   [!] No results found.")
        except Exception as e:
            print(f"   [ERROR] {e}")
        print("-" * 60)

if __name__ == "__main__":
    main()