import pandas as pd
import ast
import re
import os

# 1. Namespaces & Prefixes (Manual Definition)
PREFIXES = """@prefix er: <http://www.semanticweb.org/fall2025/eldenring/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix weapon: <http://www.semanticweb.org/fall2025/eldenring/Weapon/> .
@prefix shield: <http://www.semanticweb.org/fall2025/eldenring/Shield/> .
@prefix armor: <http://www.semanticweb.org/fall2025/eldenring/Armor/> .
@prefix talisman: <http://www.semanticweb.org/fall2025/eldenring/Talisman/> .
@prefix boss: <http://www.semanticweb.org/fall2025/eldenring/Boss/> .
@prefix npc: <http://www.semanticweb.org/fall2025/eldenring/NPC/> .
@prefix creature: <http://www.semanticweb.org/fall2025/eldenring/Creature/> .
@prefix location: <http://www.semanticweb.org/fall2025/eldenring/Location/> .
@prefix sorcery: <http://www.semanticweb.org/fall2025/eldenring/Sorcery/> .
@prefix incantation: <http://www.semanticweb.org/fall2025/eldenring/Incantation/> .
@prefix item: <http://www.semanticweb.org/fall2025/eldenring/Item/> .
@prefix ashofwar: <http://www.semanticweb.org/fall2025/eldenring/AshOfWar/> .
@prefix skill: <http://www.semanticweb.org/fall2025/eldenring/Skill/> .
@prefix material: <http://www.semanticweb.org/fall2025/eldenring/Material/> .
@prefix keyitem: <http://www.semanticweb.org/fall2025/eldenring/KeyItem/> .
@prefix ammo: <http://www.semanticweb.org/fall2025/eldenring/Ammo/> .
@prefix attribute: <http://www.semanticweb.org/fall2025/eldenring/Attribute/> .
@prefix remembrance: <http://www.semanticweb.org/fall2025/eldenring/Remembrance/> .
@prefix cookbook: <http://www.semanticweb.org/fall2025/eldenring/Cookbook/> .
@prefix whetblade: <http://www.semanticweb.org/fall2025/eldenring/Whetblade/> .
@prefix affinity: <http://www.semanticweb.org/fall2025/eldenring/Affinity/> .
@prefix consumable: <http://www.semanticweb.org/fall2025/eldenring/Consumable/> .
@prefix tool: <http://www.semanticweb.org/fall2025/eldenring/Tool/> .
@prefix greatrune: <http://www.semanticweb.org/fall2025/eldenring/GreatRune/> .
@prefix crystaltear: <http://www.semanticweb.org/fall2025/eldenring/CrystalTear/> .
@prefix bellbearing: <http://www.semanticweb.org/fall2025/eldenring/BellBearing/> .
@prefix multiplayeritem: <http://www.semanticweb.org/fall2025/eldenring/MultiplayerItem/> .
@prefix upgradematerial: <http://www.semanticweb.org/fall2025/eldenring/UpgradeMaterial/> .
@prefix weaponupgrade: <http://www.semanticweb.org/fall2025/eldenring/WeaponUpgrade/> .
@prefix shieldupgrade: <http://www.semanticweb.org/fall2025/eldenring/ShieldUpgrade/> .
@prefix spiritash: <http://www.semanticweb.org/fall2025/eldenring/SpiritAsh/> .

"""

# 2. Helpers (Optimized for String Operations)
ALPHANUM_PATTERN = re.compile(r'[^a-zA-Z0-9]')

def clean_uri_name(text):
    if pd.isna(text) or text == "": return "Unknown"
    text = str(text).title().replace(" ", "").replace("'", "").replace("-", "").replace("\"", "")
    return ALPHANUM_PATTERN.sub('', text)

def escape_literal(text):
    """Escapes strings for Turtle format"""
    if pd.isna(text): return ""
    clean = str(text).replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
    return f'"{clean}"^^xsd:string'

def parse_complex_column(cell_value):
    if pd.isna(cell_value): return None
    try:
        if str(cell_value).strip().startswith(('[', '{')):
            return ast.literal_eval(str(cell_value))
    except:
        pass
    return cell_value

# 3. File Map
file_map = {
    'bosses.csv': {'prefix': 'boss', 'class': 'er:Boss', 'type_uri': 'foaf:Agent'},
    'npcs.csv': {'prefix': 'npc', 'class': 'er:NPC', 'type_uri': 'foaf:Agent'},
    'creatures.csv': {'prefix': 'creature', 'class': 'er:Creature', 'type_uri': 'foaf:Agent'},
    'locations.csv': {'prefix': 'location', 'class': 'er:Location'}, # Special logic handled in loop
    'weapons.csv': {'prefix': 'weapon', 'class': 'er:Weapon'},
    'shields.csv': {'prefix': 'shield', 'class': 'er:Shield'},
    'armors.csv': {'prefix': 'armor', 'class': 'er:Armor'},
    'talismans.csv': {'prefix': 'talisman', 'class': 'er:Talisman'},
    'sorceries.csv': {'prefix': 'sorcery', 'class': 'er:Sorcery'},
    'incantations.csv': {'prefix': 'incantation', 'class': 'er:Incantation'},
    'ashesOfWar.csv': {'prefix': 'ashofwar', 'class': 'er:AshOfWar'},
    'skills.csv': {'prefix': 'skill', 'class': 'er:Skill'},
    'spiritAshes.csv': {'prefix': 'spiritash', 'class': 'er:SpiritAsh'},
    'remembrances.csv': {'prefix': 'remembrance', 'class': 'er:Remembrance'},
    'cookbooks.csv': {'prefix': 'cookbook', 'class': 'er:Cookbook'},
    'whetblades.csv': {'prefix': 'whetblade', 'class': 'er:Whetblade'},
    'materials.csv': {'prefix': 'material', 'class': 'er:Material'},
    'consumables.csv': {'prefix': 'consumable', 'class': 'er:Consumable'},
    'tools.csv': {'prefix': 'tool', 'class': 'er:Tool'},
    'keyItems.csv': {'prefix': 'keyitem', 'class': 'er:KeyItem'},
    'greatRunes.csv': {'prefix': 'greatrune', 'class': 'er:GreatRune'},
    'crystalTears.csv': {'prefix': 'crystaltear', 'class': 'er:CrystalTear'},
    'ammos.csv': {'prefix': 'ammo', 'class': 'er:Ammo'},
    'bells.csv': {'prefix': 'bellbearing', 'class': 'er:BellBearing'},
    'multi.csv': {'prefix': 'multiplayeritem', 'class': 'er:MultiplayerItem'},
    'upgradeMaterials.csv': {'prefix': 'upgradematerial', 'class': 'er:UpgradeMaterial'},
    'weapons_upgrades.csv': {'prefix': 'weaponupgrade', 'class': 'er:WeaponUpgrade', 'link_to_parent': 'weapon'},
    'shields_upgrades.csv': {'prefix': 'shieldupgrade', 'class': 'er:ShieldUpgrade', 'link_to_parent': 'shield'}
}

# 4. Main Direct Writer
def run_fast_ingestion(data_folder_path):
    output_file = "elden_ring_full.ttl"
    print(f"Starting DIRECT WRITE to {output_file}...")
    
    with open(output_file, "w", encoding="utf-8") as f:
        # Write Headers
        f.write(PREFIXES)
        
        for filename, config in file_map.items():
            file_path = os.path.join(data_folder_path, filename)
            if not os.path.exists(file_path):
                file_path = os.path.join(data_folder_path, "items", filename)
                if not os.path.exists(file_path):
                    continue
            
            print(f"Processing {filename}...")
            try:
                df = pd.read_csv(file_path, low_memory=False)
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                continue
            
            # Convert to dict for speed
            records = df.to_dict('records')
            prefix = config.get('prefix')
            class_uri = config.get('class')
            
            # Buffer for writing chunks
            chunk = []
            
            for row in records:
                name = row.get('name') or row.get('weapon name') or row.get('shield name')
                if pd.isna(name) or name == "": continue
                
                clean_name = clean_uri_name(name)
                subj = f"{prefix}:{clean_name}"
                
                # Start Triple Block
                lines = []
                lines.append(f"{subj} a {class_uri} ;")
                
                # Common Props
                lines.append(f"  rdfs:label {escape_literal(name)} ;")
                
                if 'id' in row and pd.notna(row['id']):
                    lines.append(f"  er:gameId {row['id']} ;")
                if 'description' in row:
                    lines.append(f"  rdfs:comment {escape_literal(row['description'])} ;")
                if 'image' in row:
                    lines.append(f"  foaf:depiction {escape_literal(row['image'])} ;")
                if 'weight' in row and pd.notna(row['weight']):
                    try:
                        w = float(row['weight'])
                        lines.append(f"  er:hasWeight \"{w}\"^^xsd:float ;")
                    except: pass

                # --- SPECIAL LOGIC: SCALING ---
                scaling = parse_complex_column(row.get('stat scaling'))
                if isinstance(scaling, dict):
                    for stat, grade in scaling.items():
                        if grade.strip() != "-":
                            stat_clean = clean_uri_name(stat)
                            lines.append(f"  er:scalesWith attribute:{stat_clean} ;")

                # --- SPECIAL LOGIC: LOCATIONS ---
                if filename == 'locations.csv':
                    for col_name, predicate in [('bosses', 'hasBoss'), ('npcs', 'hasNPC'), ('creatures', 'hasCreature')]:
                        items = parse_complex_column(row.get(col_name))
                        if isinstance(items, list):
                            for item in items:
                                target_type = col_name.capitalize().rstrip('s')
                                if target_type == "Bos": target_type = "Boss"
                                t_prefix = target_type.lower()
                                t_name = clean_uri_name(item)
                                lines.append(f"  er:{predicate} {t_prefix}:{t_name} ;")

                # --- SPECIAL LOGIC: REMEMBRANCES ---
                if filename == 'remembrances.csv':
                    if pd.notna(row.get('boss')):
                        b_name = clean_uri_name(row['boss'])
                        lines.append(f"  er:droppedBy boss:{b_name} ;")

                # --- SPECIAL LOGIC: UPGRADES ---
                if 'link_to_parent' in config:
                    p_prefix = config['link_to_parent']
                    p_name_raw = row.get('weapon name') or row.get('shield name')
                    if pd.notna(p_name_raw):
                        p_name = clean_uri_name(p_name_raw)
                        lines.append(f"  er:isUpgradeOf {p_prefix}:{p_name} ;")

                # Close block
                # Remove last semicolon, add dot
                final_block = "\n".join(lines)
                final_block = final_block[:-1] + " .\n"
                chunk.append(final_block)
                
                # Write chunk every 5000 rows to save RAM
                if len(chunk) >= 5000:
                    f.write("\n".join(chunk))
                    chunk = []

            # Flush remaining
            if chunk:
                f.write("\n".join(chunk))

    print("Done. File written successfully.")

if __name__ == "__main__":
    run_fast_ingestion('data')