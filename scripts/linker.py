import time
from rdflib import Graph, URIRef, Namespace, OWL, RDF, RDFS, Literal

# --- CONFIGURATION ---
INPUT_FILE = "rdf/elden_ring_full.ttl"
OUTPUT_FILE = "rdf/elden_ring_linked.ttl"

ER = Namespace("http://www.semanticweb.org/fall2025/eldenring/")
WD = Namespace("http://www.wikidata.org/entity/")

def run_linker():
    print(f"Reading {INPUT_FILE}...")
    g = Graph()
    try:
        g.parse(INPUT_FILE, format="turtle")
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found. Run converter.py first.")
        return

    # --- STEP 1: INJECT MISSING META ENTITIES ---
    # These do not exist in the game data CSVs, so we must create them manually.
    print("   [+] Injecting 'Meta' entities (Creators, Game Info)...")
    
    # Format: (Local URI, Label, Type, Wikidata ID)
    meta_entities = [
        ("er:EldenRing", "Elden Ring", "er:Concept", "Q64826862"),
        ("er:HidetakaMiyazaki", "Hidetaka Miyazaki", "er:Agent", "Q11454590"),
        ("er:GeorgeRRMartin", "George R. R. Martin", "er:Agent", "Q181677"),
        ("er:FromSoftware", "FromSoftware", "er:Faction", "Q2414469"),
        ("er:BandaiNamco", "Bandai Namco", "er:Faction", "Q1194689"),
    ]

    g.bind("er", ER)
    g.bind("owl", OWL)
    g.bind("wd", WD)

    for prefixed_uri, label, type_str, wd_id in meta_entities:
        local_name = prefixed_uri.split(":")[1]
        subj = ER[local_name]
        type_uri = ER[type_str.split(":")[1]]
        
        # Create the node
        g.add((subj, RDF.type, type_uri))
        g.add((subj, RDFS.label, Literal(label)))
        
        # Link it
        g.add((subj, OWL.sameAs, WD[wd_id]))

    # --- STEP 2: LINK GAME DATA ---
    print("   [+] Linking Game Data...")
    
    # Map: Local Graph URI -> Wikidata ID
    # We use the EXACT URIs you found in the files
    game_links = {
        "er:MaleniaBladeOfMiquella": "Q111995972", 
        "er:RanniWitchCarianLunarPrincess": "Q113454563" # <--- FIXED
    }

    count = 0
    for local_prefixed, wd_id in game_links.items():
        local_name = local_prefixed.split(":")[1]
        subj = ER[local_name]
        
        # Only link if the entity actually exists in the graph
        if (subj, None, None) in g:
            g.add((subj, OWL.sameAs, WD[wd_id]))
            print(f"      -> Linked {local_name} to {wd_id}")
            count += 1
        else:
            print(f"      [!] Warning: Entity '{local_name}' still not found in graph.")

    total = count + len(meta_entities)
    print(f"Successfully linked {total} entities to Wikidata.")
    
    print(f"Saving to {OUTPUT_FILE}...")
    g.serialize(destination=OUTPUT_FILE, format="turtle")
    print("Done.")

if __name__ == "__main__":
    run_linker()