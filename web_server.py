import os
import torch
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# --- AI & DATA IMPORTS ---
from rdflib import Graph, URIRef, Literal
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, pipeline
from rapidfuzz import process, fuzz

# --- CONFIGURATION ---
GRAPH_FILE = "rdf/elden_ring_optimized.ttl"
LLM_ID = "Qwen/Qwen2.5-7B-Instruct"

NS = {
    "er": "http://www.semanticweb.org/fall2025/eldenring/",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
}

# --- GLOBAL STATE ---
state = {
    "graph": None,
    "pipe": None,
    "entity_map": {},    # Map: "moonveil" -> "full text description"
    "entity_names": [],   # List: ["moonveil", "malenia", ...] for fuzzy search
    "property_index": {}  # NEW: Maps "arcane" -> ["Rivers of Blood", "Reduvia"]
}

def _device(): return "cuda" if torch.cuda.is_available() else "cpu"

# --- CORE LOGIC: GRAPH TO TEXT ---
def build_cheat_sheets(g: Graph):
    """
    Converts the RDF Graph into pre-calculated text blocks and builds a property index.
    """
    print("   [Indexer] building enhanced cheat sheets and property index...")
    cheat_sheet = {}
    
    # Iterate over every entity that has a label
    for s, p, o in g.triples((None, URIRef(NS["rdfs"] + "label"), None)):
        name = str(o)
        key = name.lower()
        
        info = [f"### RECORD: {name} ###"]
        
        # 1. Base Props (Weight, Desc)
        weight = g.value(s, URIRef(NS["er"] + "weight"))
        if weight: info.append(f"Weight: {weight}")
        
        desc = g.value(s, URIRef(NS["rdfs"] + "comment"))
        if desc: info.append(f"Description: {desc}")

        # 2. Stats (Max Upgrade Shadow Node)
        stats_node = g.value(s, URIRef(NS["er"] + "hasMaxStats"))
        if stats_node:
            info.append("STATS (At Max Upgrade):")
            for _, sp, so in g.triples((stats_node, None, None)):
                stat_name = sp.split("/")[-1]
                if stat_name not in ["type", "upgradePath"]:
                    info.append(f"  - {stat_name}: {so}")

        # 3. Requirements & Scaling (Also populates Property Index)
        for req in ["Strength", "Dexterity", "Intelligence", "Faith", "Arcane"]:
            # Check Requirements
            req_val = g.value(s, URIRef(NS["er"] + f"requires{req}"))
            if req_val: 
                info.append(f"Requires {req}: {req_val}")
            
            # Check Scaling (and index it)
            # This allows "What scales with Arcane?" to find this item
            scaling_uri = URIRef(NS["er"] + f"scaling{req}")
            # Note: Scaling is often on the stats_node, but we check the main entity too
            scaling_val = g.value(s, scaling_uri) or (g.value(stats_node, scaling_uri) if stats_node else None)
            
            if scaling_val:
                info.append(f"Scaling {req}: {scaling_val}")
                # Add to Property Index
                attr_key = req.lower()
                if attr_key not in state["property_index"]:
                    state["property_index"][attr_key] = []
                state["property_index"][attr_key].append(name)

        # 4. Drops / Location Chain
        sources = list(g.subjects(URIRef(NS["er"] + "drops"), s))
        sources += list(g.objects(s, URIRef(NS["er"] + "droppedBy")))
        
        if sources:
            info.append("OBTAINED FROM:")
            for boss in sources:
                b_name = g.value(boss, URIRef(NS["rdfs"] + "label"))
                if b_name:
                    locs = list(g.objects(boss, URIRef(NS["er"] + "locatedIn")))
                    loc_names = [str(g.value(l, URIRef(NS["rdfs"] + "label"))) for l in locs]
                    loc_str = f" (Location: {', '.join(loc_names)})" if loc_names else ""
                    info.append(f"  - {b_name}{loc_str}")

        # 5. Direct Location
        locs = list(g.objects(s, URIRef(NS["er"] + "locatedIn")))
        if locs:
            loc_names = [str(g.value(l, URIRef(NS["rdfs"] + "label"))) for l in locs]
            info.append(f"LOCATED IN: {', '.join(loc_names)}")
            
        # 6. Lore Mentions
        mentions = list(g.subjects(URIRef(NS["er"] + "mentions"), s))
        if mentions:
            info.append("MENTIONED IN DESCRIPTIONS OF:")
            for m in mentions[:5]:
                m_label = g.value(m, URIRef(NS["rdfs"] + "label"))
                if m_label: info.append(f"  - {m_label}")

        cheat_sheet[key] = "\n".join(info)
        
    return cheat_sheet

def hybrid_retrieve(query: str):
    """
    NEW: Checks Property Index first (for attributes), then falls back to Fuzzy Search.
    """
    found_entities = set()
    q_lower = query.lower()
    

    # Location match: if query contains a location, add all entities located there
    for s, p, o in state["graph"].triples((None, URIRef(NS["er"] + "locatedIn"), None)):
        loc_label = state["graph"].value(o, URIRef(NS["rdfs"] + "label"))
        if loc_label and str(loc_label).lower() in q_lower:
            item_label = state["graph"].value(s, URIRef(NS["rdfs"] + "label"))
            if item_label: found_entities.add(str(item_label).lower())

    # NEW: If the query is "List some [Category]", find all entities with that RDF type label
    from rdflib.namespace import RDF, RDFS
    for s, p, o in state["graph"].triples((None, RDF.type, None)):
        type_label = state["graph"].value(o, RDFS.label)
        if type_label and str(type_label).lower() in q_lower:
            item_label = state["graph"].value(s, RDFS.label)
            if item_label:
                found_entities.add(str(item_label).lower())

    # 1. Property Keyword Match (e.g., "arcane", "intelligence")
    for attr in state["property_index"]:
        if attr in q_lower:
            # Add top 5 items associated with this attribute to context
            found_entities.update(state["property_index"][attr][:5])
            
    # 2. Exact Substring Match (Names)
    for key in state["entity_names"]:
        if key in q_lower and len(key) > 3:
            # Recover the original display name from the map keys
            # (In a real app, you might map key -> proper_name)
            found_entities.add(key)
            
    # 3. Fuzzy Match (Smart)
    matches = process.extract(q_lower, state["entity_names"], scorer=fuzz.partial_ratio, limit=5)
    for key, score, idx in matches:
        if score > 85:
            found_entities.add(key)
            
    # 4. Final Compilation
    context = []
    # Limit to 6 entities to avoid context overflow
    for entity_key in list(found_entities)[:6]:
        # Entity keys are lowercase in our map
        lookup_key = entity_key.lower()
        if lookup_key in state["entity_map"]:
            context.append(state["entity_map"][lookup_key])
        
    return "\n\n".join(context)

# --- APP LIFECYCLE ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- SYSTEM STARTUP ---")
    
    # 1. Load Optimized Graph
    if os.path.exists(GRAPH_FILE):
        print(f"1. Loading Knowledge Graph: {GRAPH_FILE}...")
        state["graph"] = Graph()
        state["graph"].parse(GRAPH_FILE, format="turtle")
        print(f"   [Graph] Loaded {len(state['graph'])} triples.")
        
        state["entity_map"] = build_cheat_sheets(state["graph"])
        state["entity_names"] = list(state["entity_map"].keys())
        print(f"   [Index] Ready with {len(state['entity_names'])} entities.")
        print(f"   [Property Index] Mapped {len(state['property_index'])} attributes.")
    else:
        print(f"   [CRITICAL] {GRAPH_FILE} not found! Run optimize.py first.")

    # 2. Load LLM
    print("2. Loading Model (4-bit)...")
    bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
    tokenizer = AutoTokenizer.from_pretrained(LLM_ID)
    model = AutoModelForCausalLM.from_pretrained(LLM_ID, quantization_config=bnb_config, device_map="auto")
    
    state["pipe"] = pipeline(
        "text-generation", 
        model=model, 
        tokenizer=tokenizer, 
        max_new_tokens=600, 
        temperature=0.1,
        do_sample=True
    )
    
    print("   [OK] System Online.")
    yield

# --- API SETUP ---
app = FastAPI(title="EldenRAG Reasoning Server", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
templates = Jinja2Templates(directory="templates")

class ChatRequest(BaseModel): query: str

@app.get("/", response_class=HTMLResponse)
def root(request: Request): 
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat")
async def chat(request: ChatRequest):
    q = request.query
    print(f"\n--- USER QUERY: {q} ---")
    
    # 1. RETRIEVE (using new hybrid logic)
    context_text = hybrid_retrieve(q)
    
    if not context_text:
        return {
            "context": "No relevant records found.",
            "response": "I couldn't find any items, bosses, or scaling attributes in the archives matching your query."
        }

    # 2. PROMPT (Chain of Thought)
    system_prompt = f"""
    You are the "Guidance of Grace," a high-fidelity Elden Ring Knowledge Agent. 
    Your goal is to provide 100% factual answers based ONLY on the provided ARCHIVE RECORDS.

    ### 1. DATA PARSING RULES
    - Every block starts with "### RECORD: [Name] ###". 
    - "STATS (At Max Upgrade)" refers to the weapon's peak performance.
    - "OBTAINED FROM" and "LOCATED IN" are your primary links for finding where items are.
    - If a record mentions another entity (e.g., "Dropped by Magma Wyrm"), and that entity has its own RECORD below, you MUST combine that info.

    ### 2. BUILD & ATTRIBUTE LOGIC (CRITICAL)
    - If a user asks for a specific build (e.g., "Arcane", "Faith", "Intelligence"):
        a) Look at the "Scaling" section of each weapon.
        b) If the requested attribute has a letter grade (S, A, B, C, D, E), it is a VALID recommendation.
        c) If the attribute is "-" or "None", the weapon DOES NOT scale with that stat. 
        d) NEVER recommend a weapon for a build if it has no scaling for that stat, even if it has high base damage.

    ### 3. LOCATION & DISCOVERY LOGIC
    - When asked "What is in [Location]?", scan all RECORDS for "LOCATED IN: [Location]" or "OBTAINED FROM: [Boss] (Location: [Location])".
    - List every item, NPC, and Boss that matches that location string.

    ### 4. COMPARISON PROTOCOL
    - When comparing two items, use this step-by-step approach:
        - Compare Weight (Lower is usually better for carry load).
        - Compare Requirements (Which one is easier to pick up?).
        - Compare Scaling (S > A > B > C > D > E).
        - State a clear winner for the specific user's context.

    ### 5. HANDLING UNCERTAINTY
    - If the records provided do not contain the answer, say: "My current archives do not have the specific data for [X], but I can tell you about [Related Item] instead."
    - Do not hallucinate stats or locations that are not in the provided text.

    ### ARCHIVE RECORDS:
    {context_text}
    """
    
    messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": f"Answer this query using step-by-step reasoning: {q}"}
    ]
    
    prompt = state["pipe"].tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    # 3. GENERATE
    outputs = state["pipe"](prompt)
    response = outputs[0]["generated_text"].split("<|im_start|>assistant")[-1].strip()
    
    if "<|im_end|>" in response: response = response.split("<|im_end|>")[0]

    return {"context": context_text, "response": response}

if __name__ == "__main__":
    uvicorn.run("web_server:app", host="127.0.0.1", port=5000)