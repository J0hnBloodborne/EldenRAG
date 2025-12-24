import os
import json
import torch
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- IMPORTS ---
from rdflib import Graph
from sentence_transformers import SentenceTransformer, util
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, pipeline

# --- CONFIGURATION ---
GRAPH_FILE = "rdf/elden_ring_optimized.ttl"
INDEX_DIR = "rag_index"
RETRIEVAL_MODEL = "BAAI/bge-small-en-v1.5"
LLM_ID = "Qwen/Qwen2.5-7B-Instruct"

# --- GLOBAL STATE ---
state = {
    "graph": None,
    "retriever": None,
    "vectors": None,
    "entities": None,
    "pipe": None
}

def get_device(): return "cuda" if torch.cuda.is_available() else "cpu"

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- SYSTEM STARTUP ---")
    print("1. Loading Knowledge Graph...")
    state["graph"] = Graph()
    state["graph"].parse(GRAPH_FILE, format="turtle")
    
    print("2. Loading Vectors...")
    state["retriever"] = SentenceTransformer(RETRIEVAL_MODEL, device=get_device())
    state["vectors"] = torch.load(os.path.join(INDEX_DIR, "vectors.pt"), map_location=get_device())
    with open(os.path.join(INDEX_DIR, "entities.json"), "r") as f:
        state["entities"] = json.load(f)

    print(f"3. Loading {LLM_ID}...")
    bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
    tokenizer = AutoTokenizer.from_pretrained(LLM_ID)
    model = AutoModelForCausalLM.from_pretrained(LLM_ID, quantization_config=bnb_config, device_map="auto")
    
    state["pipe"] = pipeline(
        "text-generation", model=model, tokenizer=tokenizer, 
        max_new_tokens=600, temperature=0.1, do_sample=True
    )
    
    print("--- SYSTEM ONLINE ---")
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- CORE LOGIC: PRIORITY PARSER ---
def retrieve_context(query):
    # 1. VECTOR SEARCH (Increased k=5 to catch Moonveil)
    query_vec = state["retriever"].encode(query, convert_to_tensor=True)
    scores = util.cos_sim(query_vec, state["vectors"])[0]
    top_results = torch.topk(scores, k=16)
    
    context_blocks = []
    
    for idx, score in zip(top_results.indices, top_results.values):
        if score < 0.1: continue 
        
        entity = state["entities"][int(idx)]
        uri = entity["uri"]
        label = entity["label"]
        
        # 2. GRAPH WALK
        sparql = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
        
        SELECT DISTINCT ?direction ?prop ?val ?extraProp ?extraVal WHERE {{
            {{
                # OUTGOING
                <{uri}> ?p ?o .
                BIND("OUT" AS ?direction)
                BIND(?p AS ?prop)
                BIND(?o AS ?val)
                OPTIONAL {{
                    ?o ?p2 ?o2 .
                    FILTER(isIRI(?o))
                    FILTER(?p2 = er:locatedIn || ?p2 = er:drops)
                    BIND(?p2 AS ?extraProp)
                    BIND(?o2 AS ?extraVal)
                }}
            }}
            UNION
            {{
                # INCOMING
                ?s ?p <{uri}> .
                BIND("IN" AS ?direction)
                BIND(?p AS ?prop)
                BIND(?s AS ?val)
                OPTIONAL {{
                    ?s ?p2 ?o2 .
                    FILTER(?p2 = er:droppedBy || ?p2 = er:locatedIn)
                    BIND(?p2 AS ?extraProp)
                    BIND(?o2 AS ?extraVal)
                }}
            }}
            FILTER(?prop != rdfs:comment)
        }} LIMIT 50
        """
        results = state["graph"].query(sparql)
        
        # 3. PRIORITY SORTING (The Fix)
        # We bucket facts so "Hard Mechanics" appear before "Lore Trivia"
        high_priority = [] # Drops, Location, Stats
        low_priority = []  # Mentions, Flavor Text
        
        for row in results:
            direction = str(row.direction)
            prop = str(row.prop).split("/")[-1].split("#")[-1]
            val = str(row.val).split("/")[-1].split("#")[-1]
            line_text = ""

            # --- TRANSLATION & SORTING ---
            
            # CASE A: Parent/Child Relationship (Critical)
            if direction == "IN" and prop == "hasMaxStats":
                msg = f"PARENT WEAPON: This block belongs to '{val}'."
                if row.extraProp:
                    ev = str(row.extraVal).split("/")[-1].split("#")[-1]
                    msg += f" (Acquired via: {ev})"
                high_priority.insert(0, msg) # Top of the list!
                continue

            elif direction == "OUT" and prop == "hasMaxStats":
                # We skip printing the ID, we want the actual stats usually found via the reverse link
                # But we'll keep it just in case
                continue 

            # CASE B: Drops & Location (Critical)
            elif prop == "droppedBy":
                msg = f"*** ACQUISITION SOURCE ***: Dropped by {val}."
                if row.extraProp == "locatedIn":
                    ev = str(row.extraVal).split("/")[-1].split("#")[-1]
                    msg += f" (Location: {ev})"
                high_priority.append(msg)

            elif prop == "locatedIn":
                high_priority.append(f"*** LOCATION ***: Found in {val}.")

            # CASE C: Stats (Important)
            elif "attack" in prop or "scaling" in prop:
                high_priority.append(f"STAT ({prop}): {val}")

            # CASE D: The Problem Child (Mentions)
            elif prop == "mentions":
                low_priority.append(f"LORE TRIVIA (Mentions): {val}")

            elif prop == "mentionedIn":
                low_priority.append(f"LORE TRIVIA (Mentioned By): {val}")
                
            # Default
            else:
                low_priority.append(f"{prop}: {val}")

        # 4. CONSTRUCT BLOCK
        lines = [f"### RECORD: {label} ###"]
        if "text" in entity:
            desc = entity["text"].replace(label+".", "").strip()
            if len(desc) > 5: lines.append(f"Description: {desc}")
            
        # Hard facts first, then lore trivia at the bottom
        lines.extend(high_priority)
        lines.append("--- END OF CRITICAL DATA ---") 
        lines.extend(low_priority)
        
        context_blocks.append("\n".join(lines))
    
    return "\n\n".join(context_blocks)

# --- API ---
class ChatRequest(BaseModel): query: str

@app.get("/", response_class=HTMLResponse)
def root(request: Request): 
    if os.path.exists("index.html"):
        with open("index.html", "r") as f: return f.read()
    return "<h1>Backend Online.</h1>"

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    print(f"\nQUERY: {req.query}")
    context = retrieve_context(req.query)
    
    if not context:
        return {"context": "", "response": "The archives contain no records matching your inquiry."}
    
    # --- PROMPT ---
    system_prompt = """
    You are an expert Scholar of Elden Ring. 
    
    ### INSTRUCTIONS
    1. **Trust ACQUISITION SOURCE:** If a record says "*** ACQUISITION SOURCE ***", that is the absolute truth of where to get the item. 
    2. **Ignore LORE TRIVIA for Location:** If a record says "LORE TRIVIA (Mentions)", do NOT assume the item is found there. That is just backstory.
    3. **Stats:** If asked for a recommendation (e.g. Magic Katana), look for "scalingInt" or "attackMagic".
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"ARCHIVE RECORDS:\n{context}\n\nQUESTION: {req.query}"}
    ]
    
    outputs = state["pipe"](messages)
    answer = outputs[0]["generated_text"][-1]["content"]
    
    return {"context": context, "response": answer}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)