# Expanded Mappings to Wikidata (The "5-Star" Requirement)
links = {
    # --- CONCEPTS ---
    "er:EldenRing": "http://www.wikidata.org/entity/Q64525897",
    "er:TheLandsBetween": "http://www.wikidata.org/entity/Q111056538",

    # --- DEMIGODS & LEGENDS (Bosses) ---
    "er:MaleniaBladeOfMiquella": "http://www.wikidata.org/entity/Q111174620",
    "er:StarscourgeRadahn": "http://www.wikidata.org/entity/Q111174828",
    "er:GodrickTheGrafted": "http://www.wikidata.org/entity/Q111174351",
    "er:MorgottTheOmenKing": "http://www.wikidata.org/entity/Q111174783",
    "er:RykardLordOfBlasphemy": "http://www.wikidata.org/entity/Q111174808",
    "er:MohgLordOfBlood": "http://www.wikidata.org/entity/Q111174765",
    "er:MalikethTheBlackBlade": "http://www.wikidata.org/entity/Q111174635",
    "er:GodfreyFirstEldenLord": "http://www.wikidata.org/entity/Q111174345",
    "er:RennalaQueenOfTheFullMoon": "http://www.wikidata.org/entity/Q111175002",
    "er:FireGiant": "http://www.wikidata.org/entity/Q111174312",
    "er:AstelNaturalbornOfTheVoid": "http://www.wikidata.org/entity/Q111174115",
    "er:DragonlordPlacidusax": "http://www.wikidata.org/entity/Q111174260",

    # --- NPCS ---
    "er:RanniTheWitch": "http://www.wikidata.org/entity/Q111174987",
    "er:Melina": "http://www.wikidata.org/entity/Q111174720",
    "er:Blaidd": "http://www.wikidata.org/entity/Q111174152",
    "er:Fia": "http://www.wikidata.org/entity/Q111174305",
    "er:DungEater": "http://www.wikidata.org/entity/Q111174268",
    "er:IronFistAlexander": "http://www.wikidata.org/entity/Q111174102",
    "er:Patches": "http://www.wikidata.org/entity/Q111174865",

    # --- LOCATIONS ---
    "er:Limgrave": "http://www.wikidata.org/entity/Q111174615",
    "er:LiurniaOfTheLakes": "http://www.wikidata.org/entity/Q111174625",
    "er:Caelid": "http://www.wikidata.org/entity/Q111174168",
    "er:AltusPlateau": "http://www.wikidata.org/entity/Q111174105",
    "er:LeyndellRoyalCapital": "http://www.wikidata.org/entity/Q111174610",
    "er:MountaintopsOfTheGiants": "http://www.wikidata.org/entity/Q111174795",
    "er:CrumblingFarumAzula": "http://www.wikidata.org/entity/Q111174235",
    "er:SiofraRiver": "http://www.wikidata.org/entity/Q111175055",
    "er:AinselRiver": "http://www.wikidata.org/entity/Q111174095",
    "er:LakeOfRot": "http://www.wikidata.org/entity/Q111174600",
    "er:VolcanoManor": "http://www.wikidata.org/entity/Q111175150",
    "er:StormveilCastle": "http://www.wikidata.org/entity/Q111175085",
    "er:AcademyOfRayaLucaria": "http://www.wikidata.org/entity/Q111174085"
}

# 1. Read Original
input_file = "rdf/elden_ring_full.ttl"
output_file = "rdf/elden_ring_linked.ttl"

print(f"Reading {input_file}...")
try:
    with open(input_file, "r", encoding="utf-8") as f_in:
        content = f_in.read()
except FileNotFoundError:
    print(f"{input_file} not found. Run converter.py first.")
    exit()

# 2. Append Links
print(f"Injecting {len(links)} Wikidata links...")
with open(output_file, "w", encoding="utf-8") as f_out:
    f_out.write(content)
    
    f_out.write("\n\n# --- LINKED DATA BRIDGE (RUBRIC STEP 7) ---\n")
    f_out.write("@prefix owl: <http://www.w3.org/2002/07/owl#> .\n")
    
    for local, remote in links.items():
        # IMPORTANT: Use the exact prefixed subject used in the graph (e.g., boss:..., npc:...)
        # so the owl:sameAs statement attaches to an existing entity instead of creating a new URI.
        line = f"{local} owl:sameAs <{remote}> .\n"
        f_out.write(line)

print(f"Success! Saved to '{output_file}'.")