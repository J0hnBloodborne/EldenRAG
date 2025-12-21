import csv
import os
import re
import ast
from collections import defaultdict
from rdflib import Graph, Literal, RDF, RDFS, Namespace, URIRef, XSD

# --- NAMESPACES ---
ER = Namespace("http://www.semanticweb.org/fall2025/eldenring/")
SCHEMA = Namespace("http://schema.org/")
OWL = Namespace("http://www.w3.org/2002/07/owl#")

class EldenRingConverter:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.graph = Graph()
        self.graph.bind("er", ER)
        self.graph.bind("schema", SCHEMA)
        self.graph.bind("owl", OWL)
        
        # Global Registry: {"Name": URIRef}
        self.registry = {}
        # Entity List for Lore Scanning: List of (Name, URIRef)
        self.known_entities = []
        # Optimization: Pre-compiled regex for fast scanning
        self.mention_regex = None
        self.mention_map = {}
        
        # Taxonomy Mappings
        self.weapon_classes = {
            "Dagger": ER.Dagger, "Straight Sword": ER.StraightSword, "Greatsword": ER.Greatsword,
            "Colossal Sword": ER.ColossalSword, "Thrusting Sword": ER.ThrustingSword, 
            "Heavy Thrusting Sword": ER.HeavyThrustingSword, "Curved Sword": ER.CurvedSword,
            "Curved Greatsword": ER.CurvedGreatsword, "Katana": ER.Katana, "Twinblade": ER.Twinblade,
            "Axe": ER.Axe, "Greataxe": ER.Greataxe, "Hammer": ER.Hammer, "Great Hammer": ER.GreatHammer,
            "Flail": ER.Flail, "Spear": ER.Spear, "Great Spear": ER.GreatSpear, "Halberd": ER.Halberd,
            "Reaper": ER.Reaper, "Whip": ER.Whip, "Fist": ER.Fist, "Claw": ER.Claw,
            "Light Bow": ER.LightBow, "Bow": ER.Bow, "Greatbow": ER.Greatbow, "Crossbow": ER.Crossbow,
            "Ballista": ER.Ballista, "Glintstone Staff": ER.GlintstoneStaff, "Sacred Seal": ER.SacredSeal
        }

    # --- UTILITIES ---
    def clean_name(self, name):
        """Sanitizes strings for safe URI generation."""
        if not name or name == '-': return "Unknown"
        # Convert to string if it's not (just in case)
        name = str(name)
        name = re.sub(r'<[^>]+>', '', name) # Strip HTML
        name = name.replace("+", "Plus").replace("&", "And").replace("'", "")
        # PascalCase: Split by non-alphanumeric, capitalize, join
        clean = "".join(x.capitalize() for x in re.split(r'[^a-zA-Z0-9]', name) if x)
        return clean

    def parse_messy_dict(self, text):
        if not text or text.strip() in ['-', '']: return {}
        text = re.sub(r'<[^>]+>', '', text)
        try:
            return ast.literal_eval(text)
        except:
            # Regex fallback
            data = {}
            matches = re.findall(r"'([^']+)':\s*\[(.*?)\]", text)
            for key, val_str in matches:
                vals = [v.strip().strip("'\"") for v in val_str.split(',') if v.strip()]
                data[key] = vals
            return data

    def get_uri(self, name, type_hint=None):
        if not name: return None
        name = str(name).strip()
        clean = self.clean_name(name)
        uri = ER[clean]
        
        if name not in self.registry:
            self.registry[name] = uri
            self.registry[name.lower()] = uri
            
            # Register for Lore Scanner if name is distinct enough
            blacklist = {'this', 'that', 'them', 'some', 'what', 'type', 'none', 'base', 'standard', 'known', 'unknown'}
            if len(name) > 3 and name.lower() not in blacklist:
                self.known_entities.append((name, uri))
        
        if type_hint:
            self.graph.add((uri, RDF.type, type_hint))
            
        return uri

    def scan_for_mentions(self, subject_uri, text):
        """The OPTIMIZED Lore Detective."""
        if not text or not self.mention_regex: return
        
        # Find all matches in one pass (O(1) relative to entity count)
        matches = self.mention_regex.findall(text)
        
        # Link unique matches
        for name in set(matches):
            target_uri = self.mention_map.get(name)
            if target_uri and target_uri != subject_uri:
                self.graph.add((subject_uri, ER.mentions, target_uri))

    # --- PHASE 1: REGISTRY ---
    def build_registry(self):
        print("   [1/4] Building Entity Registry...")
        files_to_scan = [
            ('bosses.csv', ER.Boss), 
            ('npcs.csv', ER.NPC), 
            ('locations.csv', ER.Location),
            ('data/items/keyItems.csv', ER.KeyItem),
            ('data/items/greatRunes.csv', ER.GreatRune),
            ('weapons.csv', ER.Weapon)
        ]
        
        for fname, rtype in files_to_scan:
            path = os.path.join(self.data_dir, fname) if not fname.startswith('data/') else fname
            if not os.path.exists(path): continue
            
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('name') or row.get('weapon name')
                    if name: self.get_uri(name, type_hint=rtype)
        
        # --- OPTIMIZATION STEP ---
        print(f"   [Registry] Compiling Lore Patterns for {len(self.known_entities)} entities...")
        # Sort by length desc (so 'Malenia, Blade of Miquella' matches before 'Malenia')
        self.known_entities.sort(key=lambda x: len(x[0]), reverse=True)
        
        self.mention_map = {name: uri for name, uri in self.known_entities}
        
        # Escape names to safely use in Regex
        patterns = [re.escape(name) for name, uri in self.known_entities]
        
        # Create one giant pattern: \b(Name1|Name2|Name3)\b
        if patterns:
            self.mention_regex = re.compile(r'\b(' + '|'.join(patterns) + r')\b')

    # --- PHASE 2: PROCESSING ---
    def process_all_files(self):
        print("   [2/4] Processing Core Data & Linking Lore...")
        for root, dirs, files in os.walk(self.data_dir):
            for file in files:
                if not file.endswith('.csv'): continue
                if 'upgrades' in file: continue
                
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.dispatch_row(file, row)

    def dispatch_row(self, filename, row):
        name = row.get('name') or row.get('weapon name') or row.get('shield name')
        if not name: return

        # Explicit Typing
        type_hint = None
        if filename == 'bosses.csv': type_hint = ER.Boss
        elif filename == 'npcs.csv': type_hint = ER.NPC
        elif filename == 'locations.csv': type_hint = ER.Location
        elif filename == 'weapons.csv': type_hint = ER.Weapon
        elif filename == 'shields.csv': type_hint = ER.Shield
        elif filename == 'armors.csv': type_hint = ER.Armor
        elif filename == 'talismans.csv': type_hint = ER.Talisman
        elif filename == 'ashesOfWar.csv': type_hint = ER.AshOfWar
        elif 'spirit' in filename: type_hint = ER.SpiritAsh
        elif 'sorcer' in filename: type_hint = ER.Sorcery
        elif 'incant' in filename: type_hint = ER.Incantation
        elif 'cookbooks' in filename: type_hint = ER.Cookbook
        elif 'ammos' in filename: type_hint = ER.Ammo
        elif 'bells' in filename: type_hint = ER.BellBearing
        elif 'consumables' in filename: type_hint = ER.Consumable
        elif 'crystalTears' in filename: type_hint = ER.CrystalTear
        elif 'greatRunes' in filename: type_hint = ER.GreatRune
        elif 'keyItems' in filename: type_hint = ER.KeyItem
        elif 'materials' in filename: type_hint = ER.CraftingMaterial
        elif 'remembrances' in filename: type_hint = ER.Remembrance
        elif 'tools' in filename: type_hint = ER.Tool
        elif 'upgradeMaterials' in filename: type_hint = ER.UpgradeMaterial
        elif 'whetblades' in filename: type_hint = ER.Whetblade
        
        uri = self.get_uri(name, type_hint=type_hint)
        
        # Common Metadata
        self.graph.add((uri, RDFS.label, Literal(name)))
        if row.get('image'): self.graph.add((uri, SCHEMA.image, Literal(row['image'])))
        
        desc = row.get('description')
        if desc:
            self.graph.add((uri, RDFS.comment, Literal(desc)))
            self.scan_for_mentions(uri, desc) # Fast Scan

        # Handlers
        if filename == 'bosses.csv': self.process_boss(uri, row)
        elif filename == 'weapons.csv': self.process_weapon(uri, row)
        elif filename == 'shields.csv': self.process_shield(uri, row)
        elif filename == 'armors.csv': self.process_armor(uri, row)
        elif filename == 'talismans.csv': self.process_talisman(uri, row)
        elif filename == 'npcs.csv': self.process_npc(uri, row)
        elif 'sorcer' in filename: self.process_spell(uri, row, ER.Sorcery)
        elif 'incant' in filename: self.process_spell(uri, row, ER.Incantation)

    # --- HANDLERS (With URI Sanitation Fixes) ---
    def process_boss(self, uri, row):
        # 1. HP
        if row.get('HP'):
            clean = re.sub(r'[^\d]', '', row['HP'])
            if clean: self.graph.add((uri, ER.healthPoints, Literal(int(clean), datatype=XSD.integer)))
        
        # 2. Drops
        data = self.parse_messy_dict(row.get('Locations & Drops'))
        for loc_name, drops in data.items():
            loc_uri = self.get_uri(loc_name, ER.Location)
            if loc_uri:
                self.graph.add((uri, ER.locatedIn, loc_uri))
            
            for drop_name in drops:
                # FIX: Handle Runes properly
                # If name contains "Runes" OR is just a number (e.g. "20000" or "140,000")
                clean_drop = drop_name.replace(',', '').strip()
                
                if "Runes" in drop_name or clean_drop.isdigit():
                    # Try to extract the number
                    try:
                        # Extract digits from string like "20000 Runes" or just "20000"
                        val = int(re.sub(r'[^\d]', '', drop_name))
                        self.graph.add((uri, ER.runesDropped, Literal(val, datatype=XSD.integer)))
                    except: pass
                    continue # Skip creating an Item node
                
                # Normal Items
                drop_uri = self.get_uri(drop_name, ER.Item)
                if drop_uri:
                    self.graph.add((uri, ER.drops, drop_uri))
                    self.graph.add((drop_uri, ER.droppedBy, uri))

    def process_weapon(self, uri, row):
        cat = row.get('category')
        if cat and cat in self.weapon_classes:
            self.graph.add((uri, RDF.type, self.weapon_classes[cat]))
        else:
            self.graph.add((uri, RDF.type, ER.Weapon))

        reqs = self.parse_messy_dict(row.get('requirements'))
        for stat, val in reqs.items():
            try:
                full = {'Str': 'Strength', 'Dex': 'Dexterity', 'Int': 'Intelligence', 'Fai': 'Faith', 'Arc': 'Arcane'}.get(stat, stat)
                # FIX: clean_name the stat key
                prop_uri = ER[f"requires{self.clean_name(full)}"]
                self.graph.add((uri, prop_uri, Literal(int(val), datatype=XSD.integer)))
            except: pass
            
        scaling = self.parse_messy_dict(row.get('stat scaling'))
        for stat, val in scaling.items():
            if val != '-':
                full = {'Str': 'Strength', 'Dex': 'Dexterity', 'Int': 'Intelligence', 'Fai': 'Faith', 'Arc': 'Arcane'}.get(stat, stat)
                # FIX: clean_name the stat key
                prop_uri = ER[f"baseScaling{self.clean_name(full)}"]
                self.graph.add((uri, prop_uri, Literal(val)))

        passive = row.get('passive effect')
        if passive and passive != '-':
            self.parse_status_effect(uri, passive)

        if row.get('skill'):
            skill_uri = self.get_uri(row['skill'], ER.Skill)
            if skill_uri: self.graph.add((uri, ER.hasSkill, skill_uri))

    def process_shield(self, uri, row):
        self.graph.add((uri, RDF.type, ER.Shield))
        stats = self.parse_messy_dict(row.get('damage reduction (%)'))
        for key, val in stats.items():
            try:
                # FIX: clean_name the key
                if key == 'Bst': 
                    self.graph.add((uri, ER.guardBoost, Literal(float(val), datatype=XSD.float)))
                else: 
                    prop_uri = ER[f"negates{self.clean_name(key)}"]
                    self.graph.add((uri, prop_uri, Literal(float(val), datatype=XSD.float)))
            except: pass

    def process_armor(self, uri, row):
        self.graph.add((uri, RDF.type, ER.Armor))
        if row.get('type'):
            atype = row['type'].lower()
            if 'helm' in atype: self.graph.add((uri, RDF.type, ER.Helm))
            elif 'chest' in atype: self.graph.add((uri, RDF.type, ER.ChestArmor))
            elif 'gauntlet' in atype: self.graph.add((uri, RDF.type, ER.Gauntlets))
            elif 'leg' in atype: self.graph.add((uri, RDF.type, ER.LegArmor))
        if row.get('weight'):
            try: self.graph.add((uri, ER.weight, Literal(float(row['weight']), datatype=XSD.float)))
            except: pass

    def process_talisman(self, uri, row):
        self.graph.add((uri, RDF.type, ER.Talisman))
        if row.get('effect'): self.graph.add((uri, ER.effect, Literal(row['effect'])))

    def process_npc(self, uri, row):
        self.graph.add((uri, RDF.type, ER.NPC))
        if row.get('location'):
            loc_uri = self.get_uri(row['location'], ER.Location)
            if loc_uri: self.graph.add((uri, ER.locatedIn, loc_uri))
        if row.get('role'):
            self.graph.add((uri, ER.role, Literal(row['role'])))

    def process_spell(self, uri, row, type_class):
        self.graph.add((uri, RDF.type, type_class))
        if row.get('stamina'): self.graph.add((uri, ER.costStamina, Literal(row['stamina'])))
        if row.get('fp'): self.graph.add((uri, ER.costFP, Literal(row['fp'])))

    def parse_status_effect(self, uri, text):
        effects = [
            ("Blood Loss", ER.Hemorrhage), ("Bleed", ER.Hemorrhage),
            ("Frost", ER.Frostbite), ("Poison", ER.Poison), 
            ("Scarlet Rot", ER.ScarletRot), ("Sleep", ER.Sleep), ("Madness", ER.Madness)
        ]
        text_lower = text.lower()
        for keyword, effect_node in effects:
            if keyword.lower() in text_lower:
                self.graph.add((uri, ER.causesEffect, effect_node))
                nums = re.findall(r'\((\d+)\)', text)
                if nums:
                    self.graph.add((uri, ER.buildupAmount, Literal(int(nums[0]), datatype=XSD.integer)))

    # --- PHASE 3: SHADOW NODES (Max Upgrades) ---
    def process_upgrades(self):
        print("   [3/4] Generating Max Upgrade Nodes...")
        files = ['weapons_upgrades.csv', 'shields_upgrades.csv']
        weapon_data = defaultdict(lambda: defaultdict(dict))
        
        for fname in files:
            path = os.path.join(self.data_dir, fname)
            if not os.path.exists(path): continue
            
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('weapon name') or row.get('shield name')
                    if not name: continue
                    
                    upgrade_str = row.get('upgrade', 'Standard +0')
                    if '+' in upgrade_str:
                        parts = upgrade_str.rsplit('+', 1)
                        path_name = parts[0].strip() or "Standard"
                        try: lvl = int(parts[1])
                        except: lvl = 0
                    else:
                        path_name = "Standard"
                        lvl = 0
                    weapon_data[name][path_name][lvl] = row

        for name, paths in weapon_data.items():
            uri = self.get_uri(name)
            if not uri: continue 
            
            std = paths.get('Standard', {})
            max_std = max(std.keys()) if std else 0
            is_somber = (max_std == 10)
            self.graph.add((uri, ER.isSomber, Literal(is_somber, datatype=XSD.boolean)))
            self.graph.add((uri, ER.maxUpgradeLevel, Literal(max_std, datatype=XSD.integer)))
            
            for path_name, levels in paths.items():
                max_lvl = max(levels.keys())
                row = levels[max_lvl]
                shadow_uri = URIRef(f"{uri}_Max{path_name.replace(' ', '')}")
                
                self.graph.add((shadow_uri, RDF.type, ER.WeaponStats))
                self.graph.add((uri, ER.hasMaxStats, shadow_uri))
                self.graph.add((shadow_uri, ER.upgradePath, Literal(path_name)))
                
                # FIX: Sanitization applied here
                atk = self.parse_messy_dict(row.get('attack power'))
                for stat, val in atk.items():
                    if val != '-':
                        try: 
                            clean_stat = self.clean_name(stat) # "Sor Scaling*" -> "SorScaling"
                            self.graph.add((shadow_uri, ER[f"attack{clean_stat}"], Literal(float(val), datatype=XSD.float)))
                        except: pass
                        
                scl = self.parse_messy_dict(row.get('stat scaling'))
                for stat, val in scl.items():
                    if val != '-':
                        full = {'Str': 'Strength', 'Dex': 'Dexterity', 'Int': 'Intelligence', 'Fai': 'Faith', 'Arc': 'Arcane'}.get(stat, stat)
                        clean_stat = self.clean_name(full)
                        self.graph.add((shadow_uri, ER[f"scaling{clean_stat}"], Literal(val)))

    # --- SAVE ---
    def save(self):
        print("   [4/4] Serializing Graph...")
        output = os.path.join(os.path.dirname(self.data_dir), "rdf", "elden_ring_full.ttl")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        self.graph.serialize(destination=output, format="turtle")
        print(f"   Done. Graph size: {len(self.graph)} triples. Saved to {output}")

if __name__ == "__main__":
    converter = EldenRingConverter("data")
    converter.build_registry()
    converter.process_all_files()
    converter.process_upgrades()
    converter.save()