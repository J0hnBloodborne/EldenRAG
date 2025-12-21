import os
import json
import torch
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# --- IMPORTS ---
from rdflib import Graph
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, pipeline
from sentence_transformers import SentenceTransformer, util

# --- LOCAL MODULES ---
from intent_schema import QueryIntent, VALID_INTENTS
from executor import route_intent

# --- CONFIG ---
GRAPH_FILE = "rdf/elden_ring_optimized.ttl"
INDEX_DIR = "rag_index"
DOCS_PATH = os.path.join(INDEX_DIR, "docs.json")
EMB_PATH = os.path.join(INDEX_DIR, "embeddings.pt")

LLM_ID = "Qwen/Qwen2.5-7B-Instruct"
RETRIEVER_ID = "BAAI/bge-base-en-v1.5"

state = {
    "graph": None,
    "pipe": None,
    "bi_encoder": None,
    "embeddings": None,
    "docs": [],
    "client": None # Instructor client
}

def _device(): return "cuda" if torch.cuda.is_available() else "cpu"

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- SYSTEM STARTUP ---")
    
    # 1. Load Graph
    if os.path.exists(GRAPH_FILE):
        print(f"1. Loading GraphDB ({GRAPH_FILE})...")
        state["graph"] = Graph()
        state["graph"].parse(GRAPH_FILE, format="turtle")
    
    # 2. Load Vector Index
    if os.path.exists(DOCS_PATH):
        print("2. Loading Text Index...")
        with open(DOCS_PATH, "r", encoding="utf-8") as f: state["docs"] = json.load(f)
        state["embeddings"] = torch.load(EMB_PATH, map_location="cpu").to(_device())
    
    # 3. Load Models
    print("3. Loading Inference Engine...")
    state["bi_encoder"] = SentenceTransformer(RETRIEVER_ID, device=_device())
    
    # Use standard pipeline for generation, but we will patch it for intent extraction if possible
    # For local transformers, we can use a custom instructor adapter or just prompt engineering with the schema
    # Since we are using local transformers pipeline, we will use PROMPT ENGINEERING with the Schema to simulate extraction
    
    bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
    tokenizer = AutoTokenizer.from_pretrained(LLM_ID)
    model = AutoModelForCausalLM.from_pretrained(LLM_ID, quantization_config=bnb_config, device_map="auto", trust_remote_code=True)
    state["pipe"] = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=200, temperature=0.1)
    
    print("   [OK] System Online.")
    yield

app = FastAPI(title="EldenRAG Production", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
templates = Jinja2Templates(directory="templates")
class ChatRequest(BaseModel): query: str

# --- INTENT EXTRACTOR (Prompt Based for Local Model) ---
def extract_intent(query):
    # We construct a prompt that forces the exact JSON structure defined in intent_schema.py
    prompt = f"""
    You are an Intent Classifier. Map the user query to a JSON object.
    
    VALID INTENTS: {', '.join(VALID_INTENTS)}
    
    SCHEMA:
    {{
      "intent": "string",
      "entities": ["list", "of", "strings"],
      "attributes": ["list", "of", "strings"],
      "constraints": {{ "key": "value" }}
    }}
    
    RULES:
    - Scaling -> intent: weapon_by_scaling, attributes: [Stat], constraints: {{grade: "A"}}
    - Drops -> intent: boss_drops, entities: [BossName]
    - Requirements -> intent: weapon_by_requirements, attributes: [Stat], constraints: {{operator: "GT", value: 30}}
    
    USER: "{query}"
    JSON:
    """
    
    outputs = state["pipe"](prompt, max_new_tokens=150)
    text = outputs[0]["generated_text"]
    
    try:
        json_str = text.split("JSON:")[-1].strip()
        # Find first { and last }
        start = json_str.find("{")
        end = json_str.rfind("}") + 1
        data = json.loads(json_str[start:end])
        return QueryIntent(**data) # Validate with Pydantic
    except Exception as e:
        print(f"Intent Extraction Failed: {e}")
        return None

@app.get("/", response_class=HTMLResponse)
def root(request: Request): return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat")
async def chat(request: ChatRequest):
    q = request.query
    print(f"\n--- QUERY: {q} ---")
    
    context = None
    
    # 1. EXTRACT INTENT
    intent_obj = extract_intent(q)
    
    if intent_obj:
        print(f"   [Intent] {intent_obj}")
        
        # 2. ROUTE & EXECUTE
        sparql, error = route_intent(intent_obj)
        
        if sparql and state["graph"]:
            try:
                results = list(state["graph"].query(sparql))
                if results:
                    formatted = f"**Database Results ({intent_obj.intent}):**\n"
                    for row in results:
                        vals = [str(item).split("/")[-1] for item in row]
                        formatted += f"- {', '.join(vals)}\n"
                    context = formatted
                else:
                    context = "No exact matches found in the Archives."
            except Exception as e:
                print(f"SPARQL Error: {e}")
    
    # 3. FALLBACK (Vector)
    if not context or context == "No exact matches found in the Archives.":
        print("   [Strategy] Using Vector Search")
        q_emb = state["bi_encoder"].encode(q, convert_to_tensor=True)
        hits = util.semantic_search(q_emb, state["embeddings"], top_k=5)[0]
        context = "\n".join([state["docs"][h['corpus_id']]['text'] for h in hits])

    # 4. GENERATE RESPONSE
    messages = [
        {"role": "system", "content": f"You are Melina. Answer using this Data:\n{context}"},
        {"role": "user", "content": q}
    ]
    prompt = state["pipe"].tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    text = state["pipe"](prompt)[0]["generated_text"]
    response = text.split("<|im_start|>assistant")[-1].strip() if "<|im_start|>assistant" in text else text[len(prompt):].strip()

    return {"context": context, "response": response}

if __name__ == "__main__":
    uvicorn.run("web_server:app", host="127.0.0.1", port=5000)