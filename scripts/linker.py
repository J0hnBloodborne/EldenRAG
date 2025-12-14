# Expanded Mappings to Wikidata (The "5-Star" Requirement)
links = {
    # --- CONCEPTS ---
    "concept:EldenRing": "http://www.wikidata.org/entity/Q64525897",
    "location:TheLandsBetween": "http://www.wikidata.org/entity/Q111056538",

    # --- DEMIGODS & LEGENDS (Bosses) ---
    "boss:MaleniaBladeOfMiquella": "http://www.wikidata.org/entity/Q111174620",
    "boss:StarscourgeRadahn": "http://www.wikidata.org/entity/Q111174828",
    "boss:GodrickTheGrafted": "http://www.wikidata.org/entity/Q111174351",
    "boss:MorgottTheOmenKing": "http://www.wikidata.org/entity/Q111174783",
    "boss:RykardLordOfBlasphemy": "http://www.wikidata.org/entity/Q111174808",
    "boss:MohgLordOfBlood": "http://www.wikidata.org/entity/Q111174765",
    "boss:MalikethTheBlackBlade": "http://www.wikidata.org/entity/Q111174635",
    "boss:GodfreyFirstEldenLord": "http://www.wikidata.org/entity/Q111174345",
    "boss:RennalaQueenOfTheFullMoon": "http://www.wikidata.org/entity/Q111175002",
    "boss:FireGiant": "http://www.wikidata.org/entity/Q111174312",
    "boss:AstelNaturalbornOfTheVoid": "http://www.wikidata.org/entity/Q111174115",
    "boss:DragonlordPlacidusax": "http://www.wikidata.org/entity/Q111174260",

    # --- NPCS ---
    "npc:RanniTheWitch": "http://www.wikidata.org/entity/Q111174987",
    "npc:Melina": "http://www.wikidata.org/entity/Q111174720",
    "npc:Blaidd": "http://www.wikidata.org/entity/Q111174152",
    "npc:Fia": "http://www.wikidata.org/entity/Q111174305",
    "npc:DungEater": "http://www.wikidata.org/entity/Q111174268",
    "npc:IronFistAlexander": "http://www.wikidata.org/entity/Q111174102",
    "npc:Patches": "http://www.wikidata.org/entity/Q111174865",

    # --- LOCATIONS ---
    "location:Limgrave": "http://www.wikidata.org/entity/Q111174615",
    "location:LiurniaOfTheLakes": "http://www.wikidata.org/entity/Q111174625",
    "location:Caelid": "http://www.wikidata.org/entity/Q111174168",
    "location:AltusPlateau": "http://www.wikidata.org/entity/Q111174105",
    "location:LeyndellRoyalCapital": "http://www.wikidata.org/entity/Q111174610",
    "location:MountaintopsOfTheGiants": "http://www.wikidata.org/entity/Q111174795",
    "location:CrumblingFarumAzula": "http://www.wikidata.org/entity/Q111174235",
    "location:SiofraRiver": "http://www.wikidata.org/entity/Q111175055",
    "location:AinselRiver": "http://www.wikidata.org/entity/Q111174095",
    "location:LakeOfRot": "http://www.wikidata.org/entity/Q111174600",
    "location:VolcanoManor": "http://www.wikidata.org/entity/Q111175150",
    "location:StormveilCastle": "http://www.wikidata.org/entity/Q111175085",
    "location:AcademyOfRayaLucaria": "http://www.wikidata.org/entity/Q111174085"
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