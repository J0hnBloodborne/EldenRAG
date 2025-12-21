from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Literal

class QueryIntent(BaseModel):
    intent: str
    entities: List[str] = Field(default_factory=list)
    attributes: List[str] = Field(default_factory=list)
    constraints: Dict[str, str] = Field(default_factory=dict)
    depth: int = Field(default=1)

    @field_validator('depth')
    def check_depth(cls, v):
        return min(v, 2)

# --- COMPLETE INTENT REGISTRY ---
VALID_INTENTS = [
    # Weapon & Gear
    "weapon_lookup", "weapon_comparison", "weapon_by_scaling", 
    "weapon_by_damage_type", "weapon_by_requirements", "weapon_upgrade_path", 
    "weapon_skill_lookup",
    
    # Armor
    "armor_lookup", "armor_set_lookup", "armor_by_defense", 
    "armor_by_weight", "armor_comparison",
    
    # Items & Skills
    "item_lookup", "item_effects", "skill_lookup", "skill_by_weapon_class",
    
    # Bosses & Combat
    "boss_lookup", "boss_drops", "boss_weaknesses", "boss_location", "boss_related_items",
    
    # World
    "location_lookup", "location_items", "location_bosses", 
    "npc_lookup", "npc_related_items", "npc_locations",
    
    # Lore
    "entity_relationships", "mentions_trace", "shared_references", 
    "lineage_trace", "faction_association", "event_participation", "symbolic_association",
    
    # Analytics
    "compare_stat_distribution", "top_k_by_attribute", "cooccurrence_analysis", 
    "progression_dependency", "equipment_synergy"
]