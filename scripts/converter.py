import csv
import json
import os
import ast
import re
from rdflib import Graph, Literal, RDF, RDFS, Namespace, URIRef, XSD

# Namespaces
ER = Namespace("http://example.org/elden_ring/")
SCHEMA = Namespace("http://schema.org/")

def clean_name(name):
    """
    Converts a name into a valid URI fragment.
    e.g., "Hand-to-Hand Arts" -> "HandToHandArts"
    "Crimson Amber Medallion +1 Variant" -> "CrimsonAmberMedallionPlus1Variant"
    """
    if not name:
        return "Unknown"
    
    # Replace specific characters
    name = name.replace("+", "Plus")
    name = name.replace("&", "And")
    
    # Remove invalid characters
    name = re.sub(r'[^a-zA-Z0-9\s]', '', name)
    
    # CamelCase
    return "".join(word.capitalize() for word in name.split())

def parse_python_dict(dict_str):
    """
    Parses a string representation of a Python dictionary.
    Handles cases where the string might be malformed or empty.
    """
    if not dict_str:
        return {}
    try:
        # Fix potential issues with unquoted keys if necessary, 
        # but ast.literal_eval handles standard python dict strings well.
        return ast.literal_eval(dict_str)
    except (ValueError, SyntaxError):
        # Fallback or logging could go here
        # print(f"Warning: Could not parse dict string: {dict_str}")
        return {}

def get_files(data_dir):
    """
    Recursively finds all CSV files in the data directory.
    """
    csv_files = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith(".csv"):
                csv_files.append(os.path.join(root, file))
    return csv_files

class EldenRingConverter:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.graph = Graph()
        self.graph.bind("er", ER)
        self.graph.bind("schema", SCHEMA)
        
        # Registry: name -> URI
        self.registry = {}
        
        # Category mapping for Weapons
        self.weapon_category_map = {
            "Daggers": ER.Dagger,
            "Straight Swords": ER.StraightSword,
            "Greatswords": ER.Greatsword,
            "Colossal Swords": ER.ColossalSword,
            "Thrusting Swords": ER.ThrustingSword,
            "Heavy Thrusting Swords": ER.HeavyThrustingSword,
            "Curved Swords": ER.CurvedSword,
            "Curved Greatswords": ER.CurvedGreatsword,
            "Katanas": ER.Katana,
            "Twinblades": ER.Twinblade,
            "Axes": ER.Axe,
            "Greataxes": ER.Greataxe,
            "Hammers": ER.Hammer,
            "Flails": ER.Flail,
            "Great Hammers": ER.GreatHammer,
            "Colossal Weapons": ER.ColossalWeapon,
            "Spears": ER.Spear,
            "Great Spears": ER.GreatSpear,
            "Halberds": ER.Halberd,
            "Reapers": ER.Reaper,
            "Whips": ER.Whip,
            "Fists": ER.Fist,
            "Claws": ER.Claw,
            "Light Bows": ER.LightBow,
            "Bows": ER.Bow,
            "Greatbows": ER.Greatbow,
            "Crossbows": ER.Crossbow,
            "Ballistae": ER.Ballista,
            "Glintstone Staffs": ER.GlintstoneStaff,
            "Sacred Seals": ER.SacredSeal,
            "Torches": ER.Torch,
            "Shields": ER.Shield,
            "Small Shields": ER.SmallShield,
            "Medium Shields": ER.MediumShield,
            "Greatshields": ER.Greatshield,
            "Thrusting Shields": ER.ThrustingShield,
            "Hand-to-Hand Arts": ER.HandToHandArt,
            "Perfume Bottles": ER.PerfumeBottle,
            "Throwing Blades": ER.ThrowingBlade,
            "Backhand Blades": ER.BackhandBlade,
            "Light Greatswords": ER.LightGreatsword,
            "Great Katanas": ER.GreatKatana,
            "Beast Claws": ER.BeastClaw
        }

    def build_registry(self):
        """
        Pass 1: Scan all files and build a registry of Name -> URI.
        This allows us to link entities even if they appear in different files.
        """
        print("Building Registry...")
        files = get_files(self.data_dir)
        
        for file_path in files:
            filename = os.path.basename(file_path)
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'name' in row and row['name']:
                        name = row['name'].strip()
                        uri = ER[clean_name(name)]
                        self.registry[name] = uri
                        
                        # Also register by ID if available (optional, but good for debugging)
                        # if 'id' in row:
                        #     self.registry[f"{filename}:{row['id']}"] = uri

    def convert(self):
        """
        Pass 2: Generate RDF triples.
        """
        print("Converting Data...")
        files = get_files(self.data_dir)
        
        for file_path in files:
            filename = os.path.basename(file_path)
            print(f"Processing {filename}...")
            
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.process_row(filename, row)
        
        # Serialize
        output_path = os.path.join(os.path.dirname(self.data_dir), "rdf", "elden_ring_full.ttl")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        self.graph.serialize(destination=output_path, format="turtle")
        print(f"Conversion complete. Saved to {output_path}")

    def process_row(self, filename, row):
        name = row.get('name')
        if not name and 'weapon name' in row:
            name = row['weapon name']
            
        if not name:
            return

        name = name.strip()
        uri = self.registry.get(name)
        if not uri:
            uri = ER[clean_name(name)] # Fallback

        # Only add label/desc/image if it's the main entry (not an upgrade row)
        if filename != 'weapons_upgrades.csv':
            self.graph.add((uri, RDFS.label, Literal(name)))
            
            # Common fields
            if 'description' in row and row['description']:
                self.graph.add((uri, SCHEMA.description, Literal(row['description'])))
            if 'image' in row and row['image']:
                self.graph.add((uri, SCHEMA.image, Literal(row['image'])))

        # Dispatch based on filename/content
        if filename == 'weapons.csv':
            self.process_weapon(uri, row)
        elif filename == 'weapons_upgrades.csv':
            self.process_weapon_upgrade(uri, row)
        elif filename == 'armors.csv':
            self.process_armor(uri, row)
        elif filename == 'talismans.csv':
            self.process_talisman(uri, row)
        elif filename == 'bosses.csv':
            self.process_boss(uri, row)
        elif filename == 'remembrances.csv':
            self.process_remembrance(uri, row)
        elif filename == 'locations.csv':
            self.graph.add((uri, RDF.type, ER.Location))
        elif filename == 'creatures.csv':
            self.graph.add((uri, RDF.type, ER.Creature))
        elif filename == 'npcs.csv':
            self.graph.add((uri, RDF.type, ER.NPC))
        elif filename == 'ashesOfWar.csv':
            self.graph.add((uri, RDF.type, ER.AshOfWar))
        elif filename == 'sorceries.csv':
            self.graph.add((uri, RDF.type, ER.Sorcery))
        elif filename == 'incantations.csv':
            self.graph.add((uri, RDF.type, ER.Incantation))
        elif filename == 'spiritAshes.csv':
            self.graph.add((uri, RDF.type, ER.SpiritAsh))
        else:
            # Generic Item fallback
            self.graph.add((uri, RDF.type, ER.Item))

    def process_weapon(self, uri, row):
        # Type mapping
        category = row.get('category')
        if category and category in self.weapon_category_map:
            self.graph.add((uri, RDF.type, self.weapon_category_map[category]))
        else:
            self.graph.add((uri, RDF.type, ER.Weapon))
            if category:
                self.graph.add((uri, ER.weaponCategory, Literal(category)))

        # Requirements
        reqs_str = row.get('requirements')
        if reqs_str:
            reqs = parse_python_dict(reqs_str)
            for stat, value in reqs.items():
                try:
                    val_int = int(value)
                    if stat == 'Str': self.graph.add((uri, ER.requiresStrength, Literal(val_int, datatype=XSD.integer)))
                    elif stat == 'Dex': self.graph.add((uri, ER.requiresDexterity, Literal(val_int, datatype=XSD.integer)))
                    elif stat == 'Int': self.graph.add((uri, ER.requiresIntelligence, Literal(val_int, datatype=XSD.integer)))
                    elif stat == 'Fai': self.graph.add((uri, ER.requiresFaith, Literal(val_int, datatype=XSD.integer)))
                    elif stat == 'Arc': self.graph.add((uri, ER.requiresArcane, Literal(val_int, datatype=XSD.integer)))
                except ValueError:
                    pass

        # Damage Type
        if row.get('damage type'):
            self.graph.add((uri, ER.damageType, Literal(row['damage type'])))
        
        # Passive
        if row.get('passive effect'):
            self.graph.add((uri, ER.passiveEffect, Literal(row['passive effect'])))

        # Skill
        if row.get('skill'):
            skill_name = row['skill']
            # Try to link to Ash of War if it exists
            skill_uri = self.registry.get(skill_name)
            if skill_uri:
                self.graph.add((uri, ER.hasSkill, skill_uri))
            else:
                self.graph.add((uri, ER.hasSkillName, Literal(skill_name)))

    def process_weapon_upgrade(self, uri, row):
        # Only process base stats (Standard +0)
        # The CSV has "Standard " (with space)
        upgrade = row.get('upgrade', '').strip()
        if upgrade != 'Standard':
            return

        # Scaling
        scaling_str = row.get('stat scaling')
        if scaling_str:
            scaling = parse_python_dict(scaling_str)
            for stat, value in scaling.items():
                value = value.strip()
                if value == '-': continue
                
                if stat == 'Str': self.graph.add((uri, ER.scalingStrength, Literal(value)))
                elif stat == 'Dex': self.graph.add((uri, ER.scalingDexterity, Literal(value)))
                elif stat == 'Int': self.graph.add((uri, ER.scalingIntelligence, Literal(value)))
                elif stat == 'Fai': self.graph.add((uri, ER.scalingFaith, Literal(value)))
                elif stat == 'Arc': self.graph.add((uri, ER.scalingArcane, Literal(value)))

    def process_armor(self, uri, row):
        armor_type = row.get('type')
        if armor_type == 'helm': self.graph.add((uri, RDF.type, ER.Helm))
        elif armor_type == 'chest armor': self.graph.add((uri, RDF.type, ER.ChestArmor)) # CSV usually says "chest armor" or similar? Need to check.
        elif armor_type == 'gauntlets': self.graph.add((uri, RDF.type, ER.Gauntlets))
        elif armor_type == 'leg armor': self.graph.add((uri, RDF.type, ER.LegArmor))
        else:
            self.graph.add((uri, RDF.type, ER.Armor))
        
        # Stats (Damage Negation)
        negation_str = row.get('damage negation')
        if negation_str:
            # Sometimes it's a list of dicts in the CSV string: "[{'Phy': ...}]"
            # We need to handle that.
            try:
                data = ast.literal_eval(negation_str)
                if isinstance(data, list) and len(data) > 0:
                    stats = data[0]
                elif isinstance(data, dict):
                    stats = data
                else:
                    stats = {}
                
                for key, val in stats.items():
                    try:
                        val_float = float(val)
                        if key == 'Phy': self.graph.add((uri, ER.physicalNegation, Literal(val_float, datatype=XSD.float)))
                        elif key == 'Mag': self.graph.add((uri, ER.magicNegation, Literal(val_float, datatype=XSD.float)))
                        elif key == 'Fir': self.graph.add((uri, ER.fireNegation, Literal(val_float, datatype=XSD.float)))
                        elif key == 'Lit': self.graph.add((uri, ER.lightningNegation, Literal(val_float, datatype=XSD.float)))
                        elif key == 'Hol': self.graph.add((uri, ER.holyNegation, Literal(val_float, datatype=XSD.float)))
                    except ValueError:
                        pass
            except:
                pass

    def process_talisman(self, uri, row):
        self.graph.add((uri, RDF.type, ER.Talisman))
        if row.get('effect'):
            self.graph.add((uri, ER.effect, Literal(row['effect'])))
        if row.get('weight'):
            try:
                self.graph.add((uri, ER.weight, Literal(float(row['weight']), datatype=XSD.float)))
            except:
                pass

    def process_boss(self, uri, row):
        self.graph.add((uri, RDF.type, ER.Boss))
        if row.get('HP'):
            self.graph.add((uri, ER.healthPoints, Literal(row['HP'])))
        
        # Drops & Locations
        # Format: "{'Location Name': ['Drop 1', 'Drop 2']}"
        drops_str = row.get('Locations & Drops')
        if drops_str:
            try:
                drops_data = parse_python_dict(drops_str)
                for loc_name, items in drops_data.items():
                    # Link Location
                    # Clean location name (remove trailing colon if present)
                    loc_clean = loc_name.strip().rstrip(':')
                    loc_uri = self.registry.get(loc_clean)
                    
                    if not loc_uri:
                        # Create a stub location if not found
                        loc_uri = ER[clean_name(loc_clean)]
                        self.graph.add((loc_uri, RDF.type, ER.Location))
                        self.graph.add((loc_uri, RDFS.label, Literal(loc_clean)))
                    
                    self.graph.add((uri, ER.locatedAt, loc_uri))
                    
                    # Link Drops
                    for item_name in items:
                        # Clean item name (sometimes has amounts like "120,000")
                        # If it looks like a number, it's probably runes, ignore for now or add as runes
                        if any(char.isdigit() for char in item_name) and "Runes" not in item_name and "Bell Bearing" not in item_name:
                             # Heuristic: if it's just a number string like '120,000', skip
                             # But 'Smithing Stone [1]' has digits.
                             # Let's just try to look it up.
                             pass
                        
                        item_uri = self.registry.get(item_name)
                        if item_uri:
                            self.graph.add((uri, ER.drops, item_uri))
                        else:
                            # Maybe create a stub drop?
                            pass

            except Exception as e:
                # print(f"Error parsing drops for {row['name']}: {e}")
                pass

    def process_remembrance(self, uri, row):
        self.graph.add((uri, RDF.type, ER.Remembrance))
        
        # Link to Boss
        boss_name = row.get('boss')
        if boss_name:
            boss_uri = self.registry.get(boss_name.strip())
            if boss_uri:
                self.graph.add((uri, ER.droppedBy, boss_uri))
                # Also inverse link if needed, but droppedBy is good
        
        # Rewards (Option 1 & 2)
        for col in ['option 1', 'option 2']:
            reward_str = row.get(col)
            if not reward_str:
                continue
                
            # Handle multiple rewards separated by '/'
            rewards = reward_str.split('/')
            for reward in rewards:
                reward = reward.strip()
                # Strip prefixes
                # Regex would be cleaner but let's stick to simple string ops for now to avoid import issues if re not imported (it is imported though)
                # "Weapon: ", "Sorcery: ", "Incantation: ", "Talisman: ", "Ash of War: "
                clean_reward = re.sub(r'^(Weapon|Sorcery|Incantation|Talisman|Ash of War|Ash of War:)\s*:?\s*', '', reward, flags=re.IGNORECASE)
                
                reward_uri = self.registry.get(clean_reward)
                if reward_uri:
                    self.graph.add((uri, ER.grantsReward, reward_uri))
                    # Also link the item back to the remembrance/boss?
                    # "obtainedFrom"
                    self.graph.add((reward_uri, ER.obtainedFrom, uri))
                else:
                    # Try fuzzy match or just log?
                    # For now, just skip or create stub?
                    # Let's create a stub if we can't find it, to ensure connectivity
                    # But registry should have it if it's in other files.
                    pass

if __name__ == "__main__":
    converter = EldenRingConverter("data")
    converter.build_registry()
    converter.convert()

