import pandas as pd
import ast
import re
import os

# 1. Namespaces
PREFIXES = """@prefix er: <http://www.semanticweb.org/fall2025/eldenring/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
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

# 2. Helpers
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

# 3. Config Map
file_map = {
    'bosses.csv': {'prefix': 'boss', 'class': 'er:Boss'},
    'npcs.csv': {'prefix': 'npc', 'class': 'er:NPC'},
    'creatures.csv': {'prefix': 'creature', 'class': 'er:Creature'},
    'locations.csv': {'prefix': 'location', 'class': 'er:Location'}, 
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

# 4. Engine
def run_final_build(data_folder_path):
    output_file = "rdf/elden_ring_full.ttl"
    print(f"Starting build -> {output_file}...")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(PREFIXES)
        
        for filename, config in file_map.items():
            file_path = os.path.join(data_folder_path, filename)
            if not os.path.exists(file_path):
                file_path = os.path.join(data_folder_path, "items", filename)
                if not os.path.exists(file_path): continue
            
            print(f"Processing {filename}...")
            try:
                df = pd.read_csv(file_path, low_memory=False)
            except: continue
            
            records = df.to_dict('records')
            prefix = config.get('prefix')
            class_uri = config.get('class')
            chunk = []
            
            for row in records:
                # Name Logic
                if filename in ['weapons_upgrades.csv', 'shields_upgrades.csv']:
                    base = row.get('weapon name') or row.get('shield name')
                    upg = row.get('upgrade')
                    if pd.isna(base): continue
                    subj = f"{prefix}:{clean_uri_name(base)}{clean_uri_name(upg)}"
                    label = f"{base} ({upg})"
                else:
                    name = row.get('name') or row.get('weapon name') or row.get('shield name')
                    if pd.isna(name) or name == "": continue
                    subj = f"{prefix}:{clean_uri_name(name)}"
                    label = name

                # Triples
                lines = [f"{subj} a {class_uri} ;", f"  rdfs:label {escape_literal(label)} ;"]
                
                if 'id' in row and pd.notna(row['id']): lines.append(f"  er:gameId {row['id']} ;")
                if 'description' in row and pd.notna(row['description']): lines.append(f"  rdfs:comment {escape_literal(row['description'])} ;")
                if 'image' in row and pd.notna(row['image']): lines.append(f"  foaf:depiction {escape_literal(row['image'])} ;")
                if 'weight' in row and pd.notna(row['weight']):
                    try: lines.append(f"  er:hasWeight \"{float(row['weight'])}\"^^xsd:float ;")
                    except: pass

                # Scaling
                scaling = parse_complex_column(row.get('stat scaling'))
                if isinstance(scaling, dict):
                    for stat, grade in scaling.items():
                        if grade.strip() not in ["-", ""]:
                            lines.append(f"  er:scalesWith attribute:{clean_uri_name(stat)} ;")

                # Locations
                if filename == 'locations.csv':
                    col_map = {'bosses':('boss','hasBoss'), 'npcs':('npc','hasNPC'), 'creatures':('creature','hasCreature')}
                    for col, (pfx, pred) in col_map.items():
                        items = parse_complex_column(row.get(col))
                        if isinstance(items, list):
                            for i in items:
                                lines.append(f"  er:{pred} {pfx}:{clean_uri_name(i)} ;")

                # Remembrances
                if filename == 'remembrances.csv' and pd.notna(row.get('boss')):
                    lines.append(f"  er:droppedBy boss:{clean_uri_name(row['boss'])} ;")

                # Cookbooks (FIXED COLUMN: 'required for')
                if filename == 'cookbooks.csv':
                    items = parse_complex_column(row.get('required for'))
                    if isinstance(items, list):
                        for i in items:
                            clean_i = clean_uri_name(i)
                            lines.append(f"  er:unlocksRecipeFor item:{clean_i} ;")
                            # STUB
                            chunk.append(f"item:{clean_i} a er:Item ; rdfs:label {escape_literal(i)} .\n")

                # Whetblades
                if filename == 'whetblades.csv':
                    desc = str(row.get('description', '')).lower() + str(row.get('usage', '')).lower()
                    affinities = ['heavy', 'keen', 'quality', 'magic', 'cold', 'fire', 'flame art', 'lightning', 'sacred', 'blood', 'poison', 'occult']
                    for aff in affinities:
                        if aff in desc:
                            clean_aff = clean_uri_name(aff)
                            lines.append(f"  er:unlocksAffinity affinity:{clean_aff} ;")
                            chunk.append(f"affinity:{clean_aff} a er:Affinity ; rdfs:label {escape_literal(aff.title())} .\n")
                
                # Upgrades
                if 'link_to_parent' in config:
                    p_prefix = config['link_to_parent']
                    p_name = row.get('weapon name') or row.get('shield name')
                    if pd.notna(p_name):
                        lines.append(f"  er:isUpgradeOf {p_prefix}:{clean_uri_name(p_name)} ;")

                # Write Block
                chunk.append("\n".join(lines)[:-1] + " .\n")
                if len(chunk) >= 5000:
                    f.write("\n".join(chunk))
                    chunk = []

            if chunk: f.write("\n".join(chunk))

    print("Full Graph Generated.")

if __name__ == "__main__":
    run_final_build('data')