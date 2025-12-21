import time
from rdflib import Graph, Namespace

# --- CONFIGURATION ---
INPUT_FILE = "rdf/elden_ring_optimized.ttl"

ER = Namespace("http://www.semanticweb.org/fall2025/eldenring/")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
WD = Namespace("http://www.wikidata.org/entity/")

def run_query(g, name, query):
    print(f"\n--- TEST: {name} ---")
    start = time.time()
    try:
        results = g.query(query)
        count = 0
        for row in results:
            # Clean up output for display
            clean_row = []
            for item in row:
                if item:
                    val = str(item).split("/")[-1] # Show just the name/fragment
                    clean_row.append(val)
                else:
                    clean_row.append("-")
            print(f"   found: {clean_row}")
            count += 1
            if count >= 10: # Limit output
                print("   ... (more results hidden)")
                break
        
        print(f"   [Success] Returned {len(results)} rows in {time.time() - start:.4f}s.")
        return len(results) > 0
    except Exception as e:
        print(f"   [FAILED] Error: {e}")
        return False

def main():
    print(f"Loading {INPUT_FILE}...")
    g = Graph()
    g.parse(INPUT_FILE, format="turtle")
    print(f"Graph loaded. {len(g)} triples.")

    # 1. THE "META BUILD" CHECK
    # "Find me a weapon that causes Hemorrhage (Bleed) AND has 'A' or 'B' Arcane scaling at Max Level."
    # Tests: Shadow Nodes, Status Effects, Complex Path Traversal
    q1 = """
    PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
    SELECT DISTINCT ?weapon ?scaling ?path
    WHERE {
        ?weapon a er:Weapon .
        ?weapon er:causesEffect er:Hemorrhage .
        
        ?weapon er:hasMaxStats ?stats .
        ?stats er:upgradePath ?path .
        ?stats er:scalingArcane ?scaling .
        
        FILTER (?scaling IN ("S", "A", "B"))
    }
    LIMIT 20
    """
    run_query(g, "High Arcane Bleed Weapons", q1)

    # 2. THE "LORE DETECTIVE"
    # "Find things that mention Malenia but are NOT dropped by her."
    # Tests: Lore Scanner, Inverse Relations, Negation
    q2 = """
    PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
    SELECT DISTINCT ?thing
    WHERE {
        ?thing er:mentions er:MaleniaBladeOfMiquella .
        FILTER NOT EXISTS { ?thing er:droppedBy er:MaleniaBladeOfMiquella }
        FILTER (?thing != er:MaleniaBladeOfMiquella)
    }
    """
    run_query(g, "References to Malenia (Non-Drop)", q2)

    # 3. THE "BOSS RUSH"
    # "List bosses with > 100,000 HP or that drop > 200,000 Runes."
    # Tests: Integer Parsing, Union, Comparison
    q3 = """
    PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
    SELECT ?boss ?hp ?runes
    WHERE {
        ?boss a er:Boss .
        OPTIONAL { ?boss er:healthPoints ?hp }
        OPTIONAL { ?boss er:runesDropped ?runes }
        FILTER (?hp > 50000 || ?runes > 200000)
    }
    ORDER BY DESC(?hp)
    """
    run_query(g, "Major Bosses (High HP/Runes)", q3)

    # 4. THE "EXTERNAL KNOWLEDGE"
    # "Find entities linked to Wikidata."
    # Tests: Linker Script
    q4 = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    SELECT ?local ?wikidata
    WHERE {
        ?local owl:sameAs ?wikidata .
    }
    """
    run_query(g, "Wikidata Links", q4)

    # 5. THE "TAXONOMY CHECK"
    # "Find all Katanas."
    # Tests: Optimize.py (Inference of SubClasses)
    q5 = """
    PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
    SELECT ?weapon
    WHERE {
        ?weapon a er:Katana .
    }
    """
    run_query(g, "Class Inference (Katanas)", q5)

if __name__ == "__main__":
    main()