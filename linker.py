import pandas as pd
import ast
import re
import os

# --- WIKIDATA MAPPINGS (Step 7: 5-Star Linked Data) ---
WIKI_LINKS = {
    "Malenia Blade of Miquella": "http://www.wikidata.org/entity/Q111174620",
    "Starscourge Radahn": "http://www.wikidata.org/entity/Q111174828",
    "Godrick the Grafted": "http://www.wikidata.org/entity/Q111174351",
    "Ranni the Witch": "http://www.wikidata.org/entity/Q111174987",
    "Elden Ring": "http://www.wikidata.org/entity/Q64525897",
    "The Lands Between": "http://www.wikidata.org/entity/Q111056538"
}

PREFIXES = """@prefix er: <http://www.semanticweb.org/fall2025/eldenring/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix boss: <http://www.semanticweb.org/fall2025/eldenring/Boss/> .
@prefix item: <http://www.semanticweb.org/fall2025/eldenring/Item/> .
@prefix location: <http://www.semanticweb.org/fall2025/eldenring/Location/> .
@prefix attribute: <http://www.semanticweb.org/fall2025/eldenring/Attribute/> .
@prefix affinity: <http://www.semanticweb.org/fall2025/eldenring/Affinity/> .
"""

ALPHANUM_PATTERN = re.compile(r'[^a-zA-Z0-9]')

def clean_uri_name(text):
    if pd.isna(text) or text == "": return "Unknown"
    text = str(text).title().replace(" ", "").replace("'", "").replace("-", "").replace("\"", "")
    return ALPHANUM_PATTERN.sub('', text)

def escape_literal(text):
    if pd.isna(text): return ""
    clean = str(text).replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
    return f'"{clean}"^^xsd:string'

def parse_complex_column(cell_value):
    if pd.isna(cell_value): return None
    try:
        if str(cell_value).strip().startswith(('[', '{')):
            return ast.literal_eval(str(cell_value))
    except: pass
    return cell_value

def run_linked_build():
    print("Starting Linked Data Build...")
    output_file = "elden_ring_full.ttl"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(PREFIXES)
        
        # 1. PROCESS BOSSES (With Linking)
        try:
            df_boss = pd.read_csv("bosses.csv")
            for row in df_boss.to_dict('records'):
                name = row.get('name')
                if not name: continue
                
                uri_name = clean_uri_name(name)
                lines = [f"boss:{uri_name} a er:Boss ;", f"  rdfs:label {escape_literal(name)} ;"]
                
                # LINKING: Check if we have a Wikidata match
                if name in WIKI_LINKS:
                    lines.append(f"  owl:sameAs <{WIKI_LINKS[name]}> ;")
                
                if pd.notna(row.get('location')):
                    loc = clean_uri_name(row['location'])
                    lines.append(f"  er:locatedIn location:{loc} ;")
                
                f.write("\n".join(lines)[:-1] + " .\n")
        except: pass

        # 2. PROCESS COOKBOOKS (Fixed Logic)
        try:
            df_cook = pd.read_csv("cookbooks.csv")
            # Find the weird column
            col = next((c for c in df_cook.columns if 'required' in c or 'item' in c), None)
            if col:
                for row in df_cook.to_dict('records'):
                    name = row.get('name')
                    if not name: continue
                    uri_name = clean_uri_name(name)
                    
                    lines = [f"er:{uri_name} a er:Cookbook ;", f"  rdfs:label {escape_literal(name)} ;"]
                    
                    items = parse_complex_column(row.get(col))
                    if isinstance(items, list):
                        for i in items:
                            i_clean = clean_uri_name(i)
                            lines.append(f"  er:unlocksRecipeFor item:{i_clean} ;")
                            # Create Stub
                            f.write(f"item:{i_clean} a er:Item ; rdfs:label {escape_literal(i)} .\n")
                    
                    f.write("\n".join(lines)[:-1] + " .\n")
        except: pass

        # 3. PROCESS WHETBLADES (Fixed Logic)
        try:
            df_whet = pd.read_csv("whetblades.csv")
            for row in df_whet.to_dict('records'):
                name = row.get('name')
                desc = str(row.get('description', '')).lower() + str(row.get('usage', '')).lower()
                uri_name = clean_uri_name(name)
                
                lines = [f"er:{uri_name} a er:Whetblade ;", f"  rdfs:label {escape_literal(name)} ;"]
                
                affinities = ['Heavy', 'Keen', 'Quality', 'Magic', 'Fire'] # Subset for example
                for aff in affinities:
                    if aff.lower() in desc:
                        lines.append(f"  er:unlocksAffinity affinity:{aff} ;")
                
                f.write("\n".join(lines)[:-1] + " .\n")
        except: pass

    print("Linked Graph Generated.")

if __name__ == "__main__":
    run_linked_build()