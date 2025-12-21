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
from rapidfuzz import process, fuzz # pip install rapidfuzz

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
    "entity_names": []   # List: ["moonveil", "malenia", ...] for fuzzy search
}

def _device(): return "cuda" if torch.cuda.is_available() else "cpu"

# --- CORE LOGIC: GRAPH TO TEXT ---
def build_cheat_sheets(g: Graph):
    """
    Converts the RDF Graph into pre-calculated text blocks for every entity.
    This runs ONCE at startup so retrieval is instant.
    """
    print("   [Indexer] building cheat sheets for all entities...")
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

        # 3. Requirements
        for req in ["Strength", "Dexterity", "Intelligence", "Faith", "Arcane"]:
            val = g.value(s, URIRef(NS["er"] + f"requires{req}"))
            if val: info.append(f"Requires {req}: {val}")

        # 4. Drops / Location Chain
        # "Who drops this?"
        sources = list(g.subjects(URIRef(NS["er"] + "drops"), s))
        sources += list(g.objects(s, URIRef(NS["er"] + "droppedBy")))
        
        if sources:
            info.append("OBTAINED FROM:")
            for boss in sources:
                b_name = g.value(boss, URIRef(NS["rdfs"] + "label"))
                if b_name:
                    # Deep dive: Where is this boss?
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

def fuzzy_retrieve(query: str):
    """
    Uses RapidFuzz to find relevant entities even with typos.
    """
    context = []
    found_keys = set()
    
    # 1. Exact Substring Match (Fast)
    q_lower = query.lower()
    for key in state["entity_names"]:
        if key in q_lower and len(key) > 3:
            found_keys.add(key)
            
    # 2. Fuzzy Match (Smart)
    # Extracts top 3 matches that resemble words in the query
    matches = process.extract(q_lower, state["entity_names"], scorer=fuzz.partial_ratio, limit=5)
    for key, score, idx in matches:
        if score > 85: # High confidence threshold
            found_keys.add(key)
            
    # 3. Retrieve Text
    for key in list(found_keys)[:4]: # Limit context to top 4 entities
        context.append(state["entity_map"][key])
        
    return "\n\n".join(context)

# --- APP LIFECYCLE ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- SYSTEM STARTUP ---")
    
    # 1. Load Graph & Build Index
    if os.path.exists(GRAPH_FILE):
        print("1. Loading Knowledge Graph...")
        state["graph"] = Graph()
        state["graph"].parse(GRAPH_FILE, format="turtle")
        print(f"   [Graph] Loaded {len(state['graph'])} triples.")
        
        # Build the fast lookup maps
        state["entity_map"] = build_cheat_sheets(state["graph"])
        state["entity_names"] = list(state["entity_map"].keys())
        print(f"   [Index] Ready with {len(state['entity_names'])} entities.")
    else:
        print("   [CRITICAL] Graph file not found!")

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
        temperature=0.1, # Low temp for factual reasoning
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
    
    # 1. RETRIEVE
    context_text = fuzzy_retrieve(q)
    
    if not context_text:
        return {
            "context": "No relevant records found.",
            "response": "I couldn't find any items or bosses in the archives matching your query. Please check the spelling."
        }

    # 2. PROMPT (Chain of Thought)
    system_prompt = f"""
    You are an Elden Ring Logical Assistant. Answer using ONLY the RECORDS below.
    
    INSTRUCTIONS:
    1. Analyze the RECORDS.
    2. THINK STEP-BY-STEP:
       - Identify the items/bosses involved.
       - Extract specific numbers (Weight, Requirements, Stats).
       - Compare them if the user asks for a comparison.
    3. Provide a clear, final answer.
    
    RECORDS:
    {context_text}
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": q}
    ]
    
    prompt = state["pipe"].tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    # 3. GENERATE
    outputs = state["pipe"](prompt)
    response = outputs[0]["generated_text"].split("<|im_start|>assistant")[-1].strip()
    
    # Cleanup
    if "<|im_end|>" in response: response = response.split("<|im_end|>")[0]

    return {"context": context_text, "response": response}

if __name__ == "__main__":
    uvicorn.run("web_server:app", host="127.0.0.1", port=5000)