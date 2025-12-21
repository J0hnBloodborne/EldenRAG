from templates.weapons import SCALING_TEMPLATES, REQUIREMENT_TEMPLATES, LOOKUP_TEMPLATES
from templates.armor import ARMOR_TEMPLATES
from templates.items import ITEM_TEMPLATES
from templates.bosses import BOSS_TEMPLATES
from templates.world import WORLD_TEMPLATES
from templates.lore import LORE_TEMPLATES
from templates.analytics import ANALYTIC_TEMPLATES

def get_valid_grades(min_grade):
    """Deterministically expands 'A' -> ['S', 'A']"""
    ranks = ["S", "A", "B", "C", "D", "E"]
    try:
        idx = ranks.index(min_grade)
        return ['"' + r + '"' for r in ranks[:idx+1]]
    except ValueError:
        return ['"S"', '"A"', '"B"', '"C"']

def route_intent(intent_data):
    """
    Master Router: Maps Intent JSON -> Valid SPARQL Query
    """
    intent = intent_data.intent
    attrs = intent_data.attributes
    entities = intent_data.entities
    con = intent_data.constraints
    
    query = None

    # --- WEAPON ROUTING ---
    if intent == "weapon_by_scaling":
        stat = attrs[0].capitalize() if attrs else "Strength"
        grade_list = get_valid_grades(con.get("grade", "C"))
        grade_str = ", ".join(grade_list)
        
        if len(attrs) >= 2:
            query = SCALING_TEMPLATES["hybrid_and"].format(stat1=attrs[0].capitalize(), stat2=attrs[1].capitalize())
        elif "infusion" in con:
            query = SCALING_TEMPLATES["scaling_with_infusion"].format(stat=stat, grade_list=grade_str, infusion=con["infusion"])
        elif "effect" in con:
            query = SCALING_TEMPLATES["scaling_with_effect"].format(stat=stat, grade_list=grade_str, effect=con["effect"])
        elif con.get("operator") == "BEST":
            query = SCALING_TEMPLATES["best_in_slot"].format(stat=stat)
        else:
            query = SCALING_TEMPLATES["grade_threshold"].format(stat=stat, grade_list=grade_str)

    elif intent == "weapon_by_requirements":
        stat = attrs[0].capitalize() if attrs else "Strength"
        val = con.get("value", 0)
        op_map = {"GT": ">", "LT": "<", "EQ": "=", "GTE": ">=", "LTE": "<="}
        operator = op_map.get(con.get("operator", "GT"), ">")
        
        if "type" in con:
            query = REQUIREMENT_TEMPLATES["req_with_type"].format(stat=stat, operator=operator, value=val, w_type=con["type"])
        else:
            query = REQUIREMENT_TEMPLATES["simple_req"].format(stat=stat, operator=operator, value=val)

    elif intent == "weapon_lookup":
        name = entities[0] if entities else "Unknown"
        if "skill" in attrs:
            query = LOOKUP_TEMPLATES["weapon_skill"].format(name=name)
        elif "location" in attrs:
            query = LOOKUP_TEMPLATES["drop_location"].format(name=name)
        else:
            query = LOOKUP_TEMPLATES["full_info"].format(name=name)

    # --- BOSS ROUTING ---
    elif intent == "boss_lookup":
        name = entities[0] if entities else "Unknown"
        query = BOSS_TEMPLATES["boss_basic"].format(name=name)

    elif intent == "boss_drops":
        name = entities[0] if entities else "Unknown"
        if "weapon" in attrs:
            query = BOSS_TEMPLATES["weapon_drops_only"].format(name=name)
        else:
            query = BOSS_TEMPLATES["all_drops"].format(name=name)

    elif intent == "boss_location":
        name = entities[0] if entities else "Unknown"
        query = BOSS_TEMPLATES["boss_exact_loc"].format(name=name)

    # --- ITEM ROUTING ---
    elif intent == "item_lookup":
        name = entities[0] if entities else "Unknown"
        # Heuristic to pick best template
        if "recipe" in attrs:
            query = ITEM_TEMPLATES["recipe_for_item"].format(name=name)
        elif "key" in attrs:
            query = ITEM_TEMPLATES["key_item_use"].format(name=name)
        else:
            query = ITEM_TEMPLATES["talisman_basic"].format(name=name) 

    elif intent == "item_effects":
        keyword = attrs[0] if attrs else "Bleed"
        if "buff" in con:
            query = ITEM_TEMPLATES["talisman_buff_search"].format(keyword=keyword)
        else:
            query = ITEM_TEMPLATES["passive_search"].format(keyword=keyword)

    # --- WORLD ROUTING ---
    elif intent == "npc_lookup":
        name = entities[0] if entities else "Unknown"
        query = WORLD_TEMPLATES["npc_basic"].format(name=name)

    elif intent == "npc_locations":
        name = entities[0] if entities else "Unknown"
        query = WORLD_TEMPLATES["npc_current_loc"].format(name=name)

    elif intent == "location_items":
        loc = entities[0] if entities else "Limgrave"
        query = WORLD_TEMPLATES["items_in_specific_loc"].format(location=loc)

    # --- LORE ROUTING ---
    elif intent == "mentions_trace":
        entity = entities[0] if entities else "Marika"
        query = LORE_TEMPLATES["mentions_in_desc"].format(entity=entity)
        
    elif intent == "entity_relationships":
        # Usually implies who mentions whom
        entity = entities[0] if entities else "Marika"
        query = LORE_TEMPLATES["mentions_in_desc"].format(entity=entity)

    # --- ANALYTICS ROUTING ---
    elif intent == "top_k_by_attribute":
        k = con.get("k", 5)
        attr = attrs[0] if attrs else "HP"
        if attr == "HP":
            query = ANALYTIC_TEMPLATES["top_hp_bosses"].format(k=k)
        elif attr == "Runes":
            query = ANALYTIC_TEMPLATES["top_rune_bosses"].format(k=k)
        elif attr == "Defense":
            query = ANALYTIC_TEMPLATES["highest_phys_def"].format(k=k)

    elif intent == "compare_stat_distribution":
        if "scaling" in attrs:
            stat = attrs[1] if len(attrs) > 1 else "Dexterity"
            grade = con.get("grade", "S")
            query = ANALYTIC_TEMPLATES["count_scaling"].format(stat=stat, grade=grade)

    # --- FALLBACK ---
    if not query:
        return None, "No matching template found for logic state."
        
    return query, None