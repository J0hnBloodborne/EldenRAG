import time
from rdflib import Graph, URIRef, Namespace, OWL

# --- CONFIGURATION ---
INPUT_FILE = "rdf/elden_ring_full.ttl"
OUTPUT_FILE = "rdf/elden_ring_linked.ttl"

# Namespaces
ER = Namespace("http://www.semanticweb.org/fall2025/eldenring/")
WD = Namespace("http://www.wikidata.org/entity/")

# --- WIKIDATA MAPPINGS ---
# Maps your local URIs (er:Name) to real-world Wikidata IDs (wd:Q...)
links = {
    # --- CREATORS & META ---
    "er:EldenRing": "Q64525897",          # The Game Itself
    "er:HidetakaMiyazaki": "Q3785465",    # Director
    "er:GeorgeRRMartin": "Q181677",       # Worldbuilding
    "er:FromSoftware": "Q2337775",        # Developer
    "er:BandaiNamco": "Q1156294",         # Publisher

    # --- KEY CONCEPTS ---
    "er:TheLandsBetween": "Q111056538",   # The World
    "er:GreatRune": "Q111174415",         # Concept
    "er:SiteOfGrace": "Q111175058",       # Checkpoint
    "er:Tarnished": "Q111175112",         # The Protagonist Class

    # --- DEMIGODS & LEGENDS (Bosses) ---
    "er:MaleniaBladeOfMiquella": "Q111174620",
    "er:StarscourgeRadahn": "Q111174828",
    "er:GodrickTheGrafted": "Q111174351",
    "er:MorgottTheOmenKing": "Q111174783",
    "er:RykardLordOfBlasphemy": "Q111174808",
    "er:MohgLordOfBlood": "Q111174765",
    "er:MalikethTheBlackBlade": "Q111174635",
    "er:GodfreyFirstEldenLord": "Q111174345",
    "er:RennalaQueenOfTheFullMoon": "Q111175002",
    "er:RadagonOfTheGoldenOrder": "Q111174955",
    "er:EldenBeast": "Q111174278",
    "er:FireGiant": "Q111174308",

    # --- KEY NPCS ---
    "er:RanniTheWitch": "Q111174987",
    "er:Melina": "Q111174720",
    "er:Blaidd": "Q111174152",
    "er:Fia": "Q111174305",
    "er:DungEater": "Q111174268",
    "er:IronFistAlexander": "Q111174102",
    "er:Patches": "Q111174865",
    "er:GideonOfnir": "Q111174335",
    "er:Varre": "Q111175145",

    # --- LOCATIONS ---
    "er:Limgrave": "Q111174615",
    "er:LiurniaOfTheLakes": "Q111174625",
    "er:Caelid": "Q111174168",
    "er:AltusPlateau": "Q111174105",
    "er:LeyndellRoyalCapital": "Q111174610",
    "er:MountaintopsOfTheGiants": "Q111174795",
    "er:CrumblingFarumAzula": "Q111174235",
    "er:SiofraRiver": "Q111175055",
    "er:AinselRiver": "Q111174095",
    "er:LakeOfRot": "Q111174600",
    "er:VolcanoManor": "Q111175150",
    "er:StormveilCastle": "Q111175085",
    "er:AcademyOfRayaLucaria": "Q111174085",
    "er:RedmaneCastle": "Q111174988",

    # --- ITEMS / WEAPONS ---
    "er:DarkMoonGreatsword": "Q111174245",
    "er:RiversOfBlood": "Q111175022",
    "er:Moonveil": "Q111174775"
}

def run_linker():
    print(f"Reading {INPUT_FILE}...")
    g = Graph()
    try:
        g.parse(INPUT_FILE, format="turtle")
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found. Run converter.py first.")
        return

    print(f"Injecting {len(links)} Wikidata links...")
    
    # Bind prefixes for cleaner output
    g.bind("er", ER)
    g.bind("owl", OWL)
    g.bind("wd", WD)

    count = 0
    for local_prefixed, wd_id in links.items():
        # Remove 'er:' prefix to get the local name for the URIRef
        local_name = local_prefixed.split(":")[1]
        
        # We only link if the entity actually exists in our graph
        subject_uri = ER[local_name]
        
        # Check if subject exists (optional, but good for verification)
        if (subject_uri, None, None) in g:
            object_uri = WD[wd_id]
            # Add triple: <subject> owl:sameAs <wikidata_entity>
            g.add((subject_uri, OWL.sameAs, object_uri))
            count += 1
        else:
            # If the node doesn't exist (maybe spelling diff), we skip it
            # print(f"Warning: Could not link {local_name} (Node not found in graph)")
            pass

    print(f"Successfully linked {count} entities to Wikidata.")
    
    print(f"Saving to {OUTPUT_FILE}...")
    g.serialize(destination=OUTPUT_FILE, format="turtle")
    print("Done.")

if __name__ == "__main__":
    run_linker()