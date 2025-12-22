import csv
import os
import re
import ast
from rdflib import Graph, Literal, RDF, RDFS, Namespace, URIRef, XSD

ER = Namespace("http://www.semanticweb.org/fall2025/eldenring/")
SCHEMA = Namespace("http://schema.org/")
OWL = Namespace("http://www.w3.org/2002/07/owl#")

class EldenRingConverter:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.graph = Graph()
        self.graph.bind("er", ER)
        self.graph.bind("owl", OWL)
        self.upgrade_cache = {} 
        self.mention_map = {}
        self.mention_regex = None

        schema_path = os.path.join(os.path.dirname(data_dir), "rdf", "elden_ring_schema.ttl")
        if os.path.exists(schema_path):
            self.graph.parse(schema_path, format="turtle")

    def clean_name(self, name):
        if not name or str(name).lower() in ['nan', 'none', '']: return None
        if isinstance(name, str) and "Runes" in name: return None 
        clean = re.sub(r'[^a-zA-Z0-9 ]', '', str(name))
        return "".join(word.capitalize() for word in clean.split())

    def parse_messy_dict(self, val):
        if not val or val == "{}": return {}
        try:
            val = val.replace("'", "'") 
            data = ast.literal_eval(val)
            return {k: v.strip() if isinstance(v, str) else v for k, v in data.items()}
        except:
            return {}

    def build_registry(self):
        print("   [+] Building Lore Registry...")
        for root, _, files in os.walk(self.data_dir):
            for file in files:
                if not file.endswith(".csv") or "upgrades" in file: continue
                with open(os.path.join(root, file), 'r', encoding='utf-8', errors='replace') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        name = row.get('name') or row.get('title')
                        if name:
                            uri = ER[self.clean_name(name)]
                            self.mention_map[name] = uri
                            if "," in name:
                                short_name = name.split(",")[0]
                                if len(short_name) > 3: self.mention_map[short_name] = uri

        sorted_names = sorted(self.mention_map.keys(), key=len, reverse=True)
        if sorted_names:
            self.mention_regex = re.compile(r'\b(' + '|'.join(map(re.escape, sorted_names)) + r')\b')

    def scan_for_mentions(self, subj_uri, text):
        if not text or not self.mention_regex: return
        matches = self.mention_regex.findall(text)
        for name in set(matches):
            target_uri = self.mention_map.get(name)
            if target_uri and target_uri != subj_uri:
                self.graph.add((subj_uri, ER.mentions, target_uri))

    # --- LOGIC HANDLERS ---
    def boss_logic(self, subj, row):
        # Description
        desc = row.get('blockquote') or row.get('description')
        if desc:
            self.graph.add((subj, RDFS.comment, Literal(desc)))
            self.scan_for_mentions(subj, desc)

        # Complex "Locations & Drops" column (Dictionary)
        ld_raw = row.get('Locations & Drops')
        if ld_raw:
            try:
                data = ast.literal_eval(ld_raw)
                if isinstance(data, dict):
                    for loc_key, drops_list in data.items():
                        clean_loc = loc_key.replace(':', '').strip()
                        if clean_loc and clean_loc.lower() != "none":
                            self.graph.add((subj, ER.locatedIn, ER[self.clean_name(clean_loc)]))
                        
                        if isinstance(drops_list, list):
                            for item in drops_list:
                                # PATCH: Fix Malenia's mashed string
                                if "Malenia's Great Rune" in item and "Remembrance" in item:
                                    self.graph.add((subj, ER.drops, ER.MaleniasGreatRune))
                                    self.graph.add((subj, ER.drops, ER.RemembranceOfTheRotGoddess))
                                    continue
                                
                                if "Runes" not in item and item.strip():
                                    self.graph.add((subj, ER.drops, ER[self.clean_name(item)]))
            except: pass
        
        # Simple "drops" column
        simple_drops = row.get('drops')
        if simple_drops and not simple_drops.startswith('{'):
            for d in simple_drops.split(','):
                d = d.strip()
                if d and "Runes" not in d:
                    self.graph.add((subj, ER.drops, ER[self.clean_name(d)]))

    def weapon_logic(self, subj, row):
        name = row.get('name')
        passive = row.get('passive effect')
        if passive and passive != '-':
            p_lower = passive.lower()
            if 'bleed' in p_lower or 'blood' in p_lower or 'hemorrhage' in p_lower:
                self.graph.add((subj, ER.causesEffect, ER.Hemorrhage))
            if 'frost' in p_lower: self.graph.add((subj, ER.causesEffect, ER.Frostbite))
            if 'poison' in p_lower: self.graph.add((subj, ER.causesEffect, ER.Poison))
            if 'rot' in p_lower: self.graph.add((subj, ER.causesEffect, ER.ScarletRot))
            if 'madness' in p_lower: self.graph.add((subj, ER.causesEffect, ER.Madness))
            if 'sleep' in p_lower: self.graph.add((subj, ER.causesEffect, ER.Sleep))

        reqs = self.parse_messy_dict(row.get('requirements') or row.get('required attributes'))
        for attr, val in reqs.items():
            full = {'Str': 'Strength', 'Dex': 'Dexterity', 'Int': 'Intelligence', 'Fai': 'Faith', 'Arc': 'Arcane'}.get(attr, attr)
            try: self.graph.add((subj, ER[f"requires{full}"], Literal(int(val), datatype=XSD.integer)))
            except: pass

        upgrade_row = self.upgrade_cache.get(name)
        source_row = upgrade_row if upgrade_row else row
        shadow_uri = URIRef(str(subj) + "_MaxStats")
        self.graph.add((subj, ER.hasMaxStats, shadow_uri))
        self.graph.add((shadow_uri, RDF.type, ER.StatBlock))
        self.graph.add((shadow_uri, RDFS.label, Literal(f"{name} (Stats)")))

        scl = self.parse_messy_dict(source_row.get('stat scaling'))
        for attr, val in scl.items():
            if val and val != '-':
                full = {'Str': 'Strength', 'Dex': 'Dexterity', 'Int': 'Intelligence', 'Fai': 'Faith', 'Arc': 'Arcane'}.get(attr, attr)
                self.graph.add((shadow_uri, ER[f"scaling{full}"], Literal(val.strip(), datatype=XSD.string)))

        atk = self.parse_messy_dict(source_row.get('attack power'))
        map_dmg = {'Phy': 'Physical', 'Mag': 'Magic', 'Fir': 'Fire', 'Lit': 'Lightning', 'Hol': 'Holy', 'Cri': 'Critical'}
        for k, val in atk.items():
            clean_k = self.clean_name(k)
            prop_suffix = map_dmg.get(k, clean_k)
            if val and val != '-':
                try: self.graph.add((shadow_uri, ER[f"attack{prop_suffix}"], Literal(float(val), datatype=XSD.float)))
                except: pass

    def location_logic(self, subj, row):
        region = row.get('region')
        if region:
            reg_uri = ER[self.clean_name(region)]
            self.graph.add((subj, ER.locatedIn, reg_uri))
            self.graph.add((reg_uri, RDF.type, ER.Location))
            self.graph.add((reg_uri, RDFS.label, Literal(region)))

    def preload_upgrades(self):
        path = os.path.join(self.data_dir, "weapons_upgrades.csv")
        if not os.path.exists(path): return
        print("   [+] Preloading Max Stats...")
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            temp_best = {}
            for row in reader:
                name = row['weapon name']
                upgrade = row['upgrade']
                if "Standard" not in upgrade and "Unique" not in upgrade:
                    if any(x in upgrade for x in ["Heavy", "Keen", "Quality", "Fire", "Lightning", "Sacred", "Magic", "Cold", "Poison", "Blood", "Occult"]): continue
                level = 0
                if "+" in upgrade:
                    try: level = int(upgrade.split("+")[1].strip())
                    except: continue
                if name not in temp_best or level > temp_best[name][0]:
                    temp_best[name] = (level, row)
            for name, (_, data) in temp_best.items():
                self.upgrade_cache[name] = data

    def map_generic(self, file_path, target_class, extra_logic=None):
        full_path = os.path.join(self.data_dir, file_path)
        if not os.path.exists(full_path): return
        print(f"   [+] Ingesting: {file_path}")
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('name') or row.get('title')
                clean = self.clean_name(name)
                if not clean: continue
                
                subj = ER[clean]
                self.graph.add((subj, RDF.type, target_class))
                self.graph.add((subj, RDFS.label, Literal(name)))
                
                desc = row.get('description')
                if desc:
                    self.graph.add((subj, RDFS.comment, Literal(desc)))
                    self.scan_for_mentions(subj, desc)
                if row.get('image'):
                    self.graph.add((subj, SCHEMA.image, Literal(row['image'])))
                
                if extra_logic:
                    extra_logic(subj, row)

    def run_all(self):
        print("--- COMMENCING FULL DATA INGESTION ---")
        self.preload_upgrades()
        self.build_registry()

        self.map_generic("bosses.csv", ER.Boss, self.boss_logic)
        self.map_generic("npcs.csv", ER.NPC, lambda s, r: self.graph.add((s, ER.locatedIn, ER[self.clean_name(r.get('location'))])) if r.get('location') else None)
        self.map_generic("creatures.csv", ER.Creature, lambda s, r: self.graph.add((s, ER.locatedIn, ER[self.clean_name(r.get('location'))])) if r.get('location') else None)

        self.map_generic("weapons.csv", ER.Weapon, self.weapon_logic)
        self.map_generic("shields.csv", ER.Shield, self.weapon_logic)
        self.map_generic("armors.csv", ER.Armor)
        self.map_generic("talismans.csv", ER.Talisman)
        self.map_generic("ashesOfWar.csv", ER.AshOfWar)
        
        self.map_generic("sorceries.csv", ER.Sorcery)
        self.map_generic("incantations.csv", ER.Incantation)
        self.map_generic("spiritAshes.csv", ER.SpiritAsh)
        self.map_generic("items/keyItems.csv", ER.KeyItem)
        self.map_generic("items/consumables.csv", ER.Consumable)
        self.map_generic("items/materials.csv", ER.Material)
        self.map_generic("items/upgradeMaterials.csv", ER.Material)
        self.map_generic("items/cookbooks.csv", ER.Cookbook)
        self.map_generic("items/bells.csv", ER.BellBearing) 
        self.map_generic("items/whetblades.csv", ER.Whetblade)
        self.map_generic("items/ammos.csv", ER.Ammo, self.weapon_logic)
        self.map_generic("items/crystalTears.csv", ER.CrystalTear)
        self.map_generic("items/greatRunes.csv", ER.GreatRune)
        self.map_generic("items/remembrances.csv", ER.Remembrance)
        self.map_generic("items/tools.csv", ER.Tool)

        self.map_generic("locations.csv", ER.Location, self.location_logic)

        output = os.path.join(os.path.dirname(self.data_dir), "rdf", "elden_ring_full.ttl")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        self.graph.serialize(destination=output, format="turtle")
        print(f"--- SUCCESS: {len(self.graph)} triples ingested ---")

if __name__ == "__main__":
    EldenRingConverter("data").run_all()