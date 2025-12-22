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
        
        self.registry = {}
        self.known_entities = []
        self.mention_regex = None
        self.mention_map = {}
        
        # FIXED: Added Plurals to mapping
        self.weapon_classes = {
            "Dagger": ER.Dagger, "Daggers": ER.Dagger,
            "Straight Sword": ER.StraightSword, "Straight Swords": ER.StraightSword,
            "Greatsword": ER.Greatsword, "Greatswords": ER.Greatsword,
            "Colossal Sword": ER.ColossalSword, "Colossal Swords": ER.ColossalSword,
            "Thrusting Sword": ER.ThrustingSword, "Thrusting Swords": ER.ThrustingSword,
            "Heavy Thrusting Sword": ER.HeavyThrustingSword, "Heavy Thrusting Swords": ER.HeavyThrustingSword,
            "Curved Sword": ER.CurvedSword, "Curved Swords": ER.CurvedSword,
            "Curved Greatsword": ER.CurvedGreatsword, "Curved Greatswords": ER.CurvedGreatsword,
            "Katana": ER.Katana, "Katanas": ER.Katana,
            "Twinblade": ER.Twinblade, "Twinblades": ER.Twinblade,
            "Axe": ER.Axe, "Axes": ER.Axe,
            "Greataxe": ER.Greataxe, "Greataxes": ER.Greataxe,
            "Hammer": ER.Hammer, "Hammers": ER.Hammer,
            "Great Hammer": ER.GreatHammer, "Great Hammers": ER.GreatHammer,
            "Flail": ER.Flail, "Flails": ER.Flail,
            "Spear": ER.Spear, "Spears": ER.Spear,
            "Great Spear": ER.GreatSpear, "Great Spears": ER.GreatSpear,
            "Halberd": ER.Halberd, "Halberds": ER.Halberd,
            "Reaper": ER.Reaper, "Reapers": ER.Reaper,
            "Whip": ER.Whip, "Whips": ER.Whip,
            "Fist": ER.Fist, "Fists": ER.Fist,
            "Claw": ER.Claw, "Claws": ER.Claw,
            "Light Bow": ER.LightBow, "Light Bows": ER.LightBow,
            "Bow": ER.Bow, "Bows": ER.Bow,
            "Greatbow": ER.Greatbow, "Greatbows": ER.Greatbow,
            "Crossbow": ER.Crossbow, "Crossbows": ER.Crossbow,
            "Ballista": ER.Ballista, "Ballistae": ER.Ballista,
            "Glintstone Staff": ER.GlintstoneStaff, "Glintstone Staffs": ER.GlintstoneStaff,
            "Sacred Seal": ER.SacredSeal, "Sacred Seals": ER.SacredSeal,
            "Torch": ER.Torch, "Torches": ER.Torch,
            "Hand-to-Hand Art": ER.HandToHandArt, "Hand-to-Hand Arts": ER.HandToHandArt,
            "Perfume Bottle": ER.PerfumeBottle, "Perfume Bottles": ER.PerfumeBottle,
            "Throwing Blade": ER.ThrowingBlade, "Throwing Blades": ER.ThrowingBlade,
            "Backhand Blade": ER.BackhandBlade, "Backhand Blades": ER.BackhandBlade,
            "Light Greatsword": ER.LightGreatsword, "Light Greatswords": ER.LightGreatsword,
            "Great Katana": ER.GreatKatana, "Great Katanas": ER.GreatKatana,
            "Beast Claw": ER.BeastClaw, "Beast Claws": ER.BeastClaw
        }

    def clean_name(self, name):
        if not name or name == '-': return "Unknown"
        name = str(name)
        name = re.sub(r'<[^>]+>', '', name)
        name = name.replace("+", "Plus").replace("&", "And").replace("'", "")
        clean = "".join(x.capitalize() for x in re.split(r'[^a-zA-Z0-9]', name) if x)
        return clean

    def parse_messy_dict(self, text):
        if not text or text.strip() in ['-', '']: return {}
        text = re.sub(r'<[^>]+>', '', text)
        try:
            return ast.literal_eval(text)
        except:
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
            blacklist = {'this', 'that', 'them', 'some', 'what', 'type', 'none', 'base', 'standard', 'known', 'unknown'}
            if len(name) > 3 and name.lower() not in blacklist:
                self.known_entities.append((name, uri))
        
        if type_hint:
            self.graph.add((uri, RDF.type, type_hint))
        return uri

    def scan_for_mentions(self, subject_uri, text):
        if not text or not self.mention_regex: return
        matches = self.mention_regex.findall(text)
        for name in set(matches):
            target_uri = self.mention_map.get(name)
            if target_uri and target_uri != subject_uri:
                self.graph.add((subject_uri, ER.mentions, target_uri))

    def build_registry(self):
        print("   [1/4] Building Entity Registry...")
        files_to_scan = [
            ('bosses.csv', ER.Boss), ('npcs.csv', ER.NPC), ('locations.csv', ER.Location),
            ('data/items/keyItems.csv', ER.KeyItem), ('data/items/greatRunes.csv', ER.GreatRune),
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
        
        print(f"   [Registry] Compiling Lore Patterns for {len(self.known_entities)} entities...")
        self.known_entities.sort(key=lambda x: len(x[0]), reverse=True)
        self.mention_map = {name: uri for name, uri in self.known_entities}
        patterns = [re.escape(name) for name, uri in self.known_entities]
        if patterns:
            self.mention_regex = re.compile(r'\b(' + '|'.join(patterns) + r')\b')

    def process_all_files(self):
        print("   [2/4] Processing Core Data & Linking Lore...")
        for root, dirs, files in os.walk(self.data_dir):
            for file in files:
                if not file.endswith('.csv') or 'upgrades' in file: continue
                with open(os.path.join(root, file), 'r', encoding='utf-8', errors='replace') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.dispatch_row(file, row)

    def dispatch_row(self, filename, row):
        name = row.get('name') or row.get('weapon name') or row.get('shield name')
        if not name: return

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
        self.graph.add((uri, RDFS.label, Literal(name)))
        if row.get('image'): self.graph.add((uri, SCHEMA.image, Literal(row['image'])))
        desc = row.get('description')
        if desc:
            self.graph.add((uri, RDFS.comment, Literal(desc)))
            self.scan_for_mentions(uri, desc)

        if filename == 'bosses.csv': self.process_boss(uri, row)
        elif filename == 'weapons.csv': self.process_weapon(uri, row)
        elif filename == 'shields.csv': self.process_shield(uri, row)
        elif filename == 'armors.csv': self.process_armor(uri, row)
        elif filename == 'talismans.csv': self.process_talisman(uri, row)
        elif filename == 'npcs.csv': self.process_npc(uri, row)
        elif 'sorcer' in filename: self.process_spell(uri, row, ER.Sorcery)
        elif 'incant' in filename: self.process_spell(uri, row, ER.Incantation)

    def process_boss(self, uri, row):
        if row.get('HP'):
            # FIX: Find First integer sequence only
            match = re.search(r'\d+', row['HP'].replace(',', ''))
            if match:
                self.graph.add((uri, ER.healthPoints, Literal(int(match.group()), datatype=XSD.integer)))
        
        data = self.parse_messy_dict(row.get('Locations & Drops'))
        for loc_name, drops in data.items():
            loc_uri = self.get_uri(loc_name, ER.Location)
            if loc_uri: self.graph.add((uri, ER.locatedIn, loc_uri))
            
            for drop_name in drops:
                clean_drop = drop_name.replace(',', '').strip()
                if "Runes" in drop_name or clean_drop.isdigit():
                    try:
                        val = int(re.sub(r'[^\d]', '', drop_name))
                        self.graph.add((uri, ER.runesDropped, Literal(val, datatype=XSD.integer)))
                    except: pass
                    continue
                
                drop_uri = self.get_uri(drop_name, ER.Item)
                if drop_uri:
                    self.graph.add((uri, ER.drops, drop_uri))
                    self.graph.add((drop_uri, ER.droppedBy, uri))

    def process_weapon(self, uri, row):
        cat = row.get('category')
        # Plural friendly check
        if cat:
            cat = cat.strip()
            if cat in self.weapon_classes:
                self.graph.add((uri, RDF.type, self.weapon_classes[cat]))
            else:
                self.graph.add((uri, RDF.type, ER.Weapon))
        else:
            self.graph.add((uri, RDF.type, ER.Weapon))

        reqs = self.parse_messy_dict(row.get('requirements'))
        for stat, val in reqs.items():
            try:
                full = {'Str': 'Strength', 'Dex': 'Dexterity', 'Int': 'Intelligence', 'Fai': 'Faith', 'Arc': 'Arcane'}.get(stat, stat)
                self.graph.add((uri, ER[f"requires{self.clean_name(full)}"], Literal(int(val), datatype=XSD.integer)))
            except: pass
            
        scaling = self.parse_messy_dict(row.get('stat scaling'))
        for stat, val in scaling.items():
            if val != '-':
                full = {'Str': 'Strength', 'Dex': 'Dexterity', 'Int': 'Intelligence', 'Fai': 'Faith', 'Arc': 'Arcane'}.get(stat, stat)
                # FIX: Strip whitespace
                self.graph.add((uri, ER[f"baseScaling{self.clean_name(full)}"], Literal(val.strip())))

        passive = row.get('passive effect')
        if passive and passive != '-':
            self.parse_status_effect(uri, passive)

        if row.get('skill'):
            skill_uri = self.get_uri(row['skill'], ER.Skill)
            if skill_uri: self.graph.add((uri, ER.hasSkill, skill_uri))
        
        if row.get('weight'):
            self.graph.add((uri, ER.weight, Literal(float(row['weight']), datatype=XSD.float)))

    def process_shield(self, uri, row):
        self.graph.add((uri, RDF.type, ER.Shield))
        stats = self.parse_messy_dict(row.get('damage reduction (%)'))
        for key, val in stats.items():
            try:
                if key == 'Bst': self.graph.add((uri, ER.guardBoost, Literal(float(val), datatype=XSD.float)))
                else: self.graph.add((uri, ER[f"negates{self.clean_name(key)}"], Literal(float(val), datatype=XSD.float)))
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
        effects = [("Blood Loss", ER.Hemorrhage), ("Bleed", ER.Hemorrhage), ("Frost", ER.Frostbite), ("Poison", ER.Poison), ("Scarlet Rot", ER.ScarletRot), ("Sleep", ER.Sleep), ("Madness", ER.Madness)]
        text_lower = text.lower()
        for keyword, effect_node in effects:
            if keyword.lower() in text_lower:
                self.graph.add((uri, ER.causesEffect, effect_node))
                nums = re.findall(r'\((\d+)\)', text)
                if nums: self.graph.add((uri, ER.buildupAmount, Literal(int(nums[0]), datatype=XSD.integer)))

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
                
                atk = self.parse_messy_dict(row.get('attack power'))
                for stat, val in atk.items():
                    if val != '-':
                        try:
                            clean_stat = self.clean_name(stat)
                            self.graph.add((shadow_uri, ER[f"attack{clean_stat}"], Literal(float(val), datatype=XSD.float)))
                        except: pass
                scl = self.parse_messy_dict(row.get('stat scaling'))
                for stat, val in scl.items():
                    if val != '-':
                        full = {'Str': 'Strength', 'Dex': 'Dexterity', 'Int': 'Intelligence', 'Fai': 'Faith', 'Arc': 'Arcane'}.get(stat, stat)
                        clean_stat = self.clean_name(full)
                        # FIX: Strip whitespace
                        self.graph.add((shadow_uri, ER[f"scaling{clean_stat}"], Literal(val.strip())))

    def save(self):
        print("   [4/4] Serializing Graph...")
        output = os.path.join(os.path.dirname(self.data_dir), "rdf", "elden_ring_full.ttl")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        self.graph.serialize(destination=output, format="turtle")
        print(f"   Done. Graph size: {len(self.graph)} triples.")

if __name__ == "__main__":
    converter = EldenRingConverter("data")
    converter.build_registry()
    converter.process_all_files()
    converter.process_upgrades()
    converter.save()