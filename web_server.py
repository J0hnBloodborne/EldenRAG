import os
import json
import time
import torch
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from rdflib import Graph

# ML Imports (Your existing stack)
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, pipeline
from sentence_transformers import SentenceTransformer, CrossEncoder, util

app = FastAPI(title="EldenRAG Final", description="Precision Reranking")

# --- CONFIGURATION ---
GRAPH_FILE = "rdf/elden_ring_linked.ttl"  # Or elden_ring_optimized.ttl
INDEX_DIR = "rag_index"
DOCS_PATH = os.path.join(INDEX_DIR, "docs.json")
EMB_PATH = os.path.join(INDEX_DIR, "embeddings.pt")

# Models (Cached locally)
RETRIEVER_ID = "BAAI/bge-base-en-v1.5"
RERANKER_ID = "cross-encoder/ms-marco-MiniLM-L-6-v2"
LLM_ID = "Qwen/Qwen2.5-7B-Instruct" 

templates = Jinja2Templates(directory="templates")

# --- GLOBAL STATE ---
state = {
    "docs": [],
    "embeddings": None,
    "bi_encoder": None,
    "cross_encoder": None,
    "llm_pipe": None,
    "graph": None
}

class QueryModel(BaseModel):
    query: str

def _device():
    return "cuda" if torch.cuda.is_available() else "cpu"

# --- LIFECYCLE: LOAD EVERYTHING ---
@app.on_event("startup")
async def startup_event():
    print("--- SYSTEM STARTUP ---")
    
    # 1. LOAD INDEX (JSON + PT)
    if not os.path.exists(DOCS_PATH) or not os.path.exists(EMB_PATH):
        print(f"[CRITICAL] Missing Index at {INDEX_DIR}. Did you run the old indexer?")
        return

    print(f"1. Loading Index from {INDEX_DIR}...")
    with open(DOCS_PATH, "r", encoding="utf-8") as f:
        state["docs"] = json.load(f)
    
    state["embeddings"] = torch.load(EMB_PATH, map_location="cpu")
    if not torch.is_tensor(state["embeddings"]):
        state["embeddings"] = torch.tensor(state["embeddings"])
    
    # Move embeddings to GPU for fast search
    state["embeddings"] = state["embeddings"].to(_device())
    print(f"   [OK] Loaded {len(state['docs'])} docs.")

    # 2. LOAD RETRIEVERS
    print("2. Loading Encoders...")
    state["bi_encoder"] = SentenceTransformer(RETRIEVER_ID, device=_device())
    state["cross_encoder"] = CrossEncoder(RERANKER_ID, device=_device())
    print("   [OK] Encoders Ready.")

    # 3. LOAD LLM (4-Bit Quantization for 3070)
    print(f"3. Loading LLM: {LLM_ID}...")
    try:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        tokenizer = AutoTokenizer.from_pretrained(LLM_ID)
        model = AutoModelForCausalLM.from_pretrained(
            LLM_ID,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True
        )
        state["llm_pipe"] = pipeline(
            "text-generation", 
            model=model, 
            tokenizer=tokenizer, 
            max_new_tokens=512,
            temperature=0.3
        )
        print("   [OK] Qwen 7B (4-bit) Ready.")
    except Exception as e:
        print(f"   [ERROR] LLM Load Failed: {e}")

    # 4. LOAD GRAPH (Optional for SPARQL)
    if os.path.exists(GRAPH_FILE):
        print("4. Loading RDF Graph...")
        state["graph"] = Graph()
        state["graph"].parse(GRAPH_FILE, format="turtle")
        print("   [OK] Graph Loaded.")

# --- SEARCH LOGIC (Your Logic) ---
def retrieve_and_rerank(query):
    # 1. Bi-Encoder Search
    q_emb = state["bi_encoder"].encode(query, convert_to_tensor=True)
    hits = util.semantic_search(q_emb, state["embeddings"], top_k=50)[0]

    # 2. Cross-Encoder Reranking
    cross_inp = [[query, state["docs"][hit['corpus_id']]['text']] for hit in hits]
    scores = state["cross_encoder"].predict(cross_inp)

    for idx in range(len(scores)):
        hits[idx]['cross_score'] = scores[idx]

    # Sort by Rerank Score
    hits = sorted(hits, key=lambda x: x['cross_score'], reverse=True)
    
    # Return Top 5
    results = []
    seen = set()
    for hit in hits[:5]:
        doc = state["docs"][hit['corpus_id']]
        # Use Title or Subject as unique key to avoid duplicates
        key = doc.get("title", doc.get("subject", "Unk"))
        if key not in seen:
            results.append(doc['text'])
            seen.add(key)
            
    return "\n\n".join(results)

# --- ROUTES ---
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat")
async def chat(request: QueryModel):
    user_query = request.query
    print(f"\n--- QUERY: {user_query} ---")
    
    # 1. Retrieve
    context = retrieve_and_rerank(user_query)
    
    # 2. Generate
    if state["llm_pipe"]:
        messages = [
            {"role": "system", "content": f"You are Melina. Use this Context to answer:\n{context}"},
            {"role": "user", "content": user_query}
        ]
        prompt = state["llm_pipe"].tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        outputs = state["llm_pipe"](prompt)
        text = outputs[0]["generated_text"]
        # Strip Prompt
        if "<|im_start|>assistant" in text:
            response = text.split("<|im_start|>assistant")[-1].strip()
        else:
            response = text[len(prompt):].strip()
    else:
        response = "LLM Offline. Context found."

    return {"context": context, "response": response}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)