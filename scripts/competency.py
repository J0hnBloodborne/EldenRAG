import os
import torch
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, pipeline

# Retrieval Imports (Using the Chroma index we built)
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# --- CONFIGURATION ---
# 1. THE INDEX WE BUILT
DB_DIR = "data/chroma_db"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# 2. THE MODEL YOU ALREADY HAVE (Standard Transformers)
# This matches the ID in your old script's logic
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct" 

# --- GLOBAL STATE ---
state = {
    "db": None,
    "pipe": None, # The HF Pipeline
    "retriever": None
}

# --- LIFECYCLE MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- SYSTEM STARTUP ---")
    
    # 1. LOAD LLM (Transformers + 4-bit Quantization)
    print(f"1. Loading Model: {MODEL_ID} (4-bit)...")
    try:
        # 4-Bit Config (Fits 7B in 8GB VRAM)
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True
        )
        
        # Create Raw Pipeline
        state["pipe"] = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=512,
            temperature=0.3,
            repetition_penalty=1.1
        )
        print("   [OK] Model Loaded (Transformers).")
    except Exception as e:
        print(f"   [CRITICAL] LLM Load Failed: {e}")
        print("   Did you install bitsandbytes? (pip install bitsandbytes accelerate)")

    # 2. LOAD RETRIEVER
    print(f"2. Loading Index: {DB_DIR}...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    if os.path.exists(DB_DIR):
        state["db"] = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
        state["retriever"] = state["db"].as_retriever(search_kwargs={"k": 5})
        print("   [OK] Database Loaded.")
    else:
        print("   [CRITICAL] Index not found. Run build_rag_index.py first.")
    
    yield
    print("--- SYSTEM SHUTDOWN ---")

# --- APP SETUP ---
app = FastAPI(title="Elden Ring RAG", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
templates = Jinja2Templates(directory="templates")

# --- DATA MODELS ---
class ChatRequest(BaseModel):
    message: str | None = None
    query: str | None = None

# --- ROUTES ---
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    user_input = request.message or request.query
    print(f"\n--- QUERY: {user_input} ---")

    if not state["pipe"]:
        return JSONResponse({"response": "Model failed to load."}, status_code=500)

    # 1. RETRIEVE (Chroma)
    docs = state["retriever"].invoke(user_input)
    print(f"   [Retrieval] Found {len(docs)} cards.")

    # 2. FORMAT CONTEXT
    context_text = ""
    for i, doc in enumerate(docs):
        name = doc.metadata.get('name', 'Unknown')
        content = doc.page_content.replace('\n', ' ')
        context_text += f"[Entity {i+1}: {name}] {content}\n"

    # 3. GENERATE (Raw Transformers)
    # ChatML Format
    messages = [
        {"role": "system", "content": (
            "You are Melina, the Kindling Maiden. Guide the Tarnished.\n"
            "Answer using ONLY the Context below.\n"
            "If the answer is missing, say 'The Golden Order is silent.'\n\n"
            f"CONTEXT:\n{context_text}"
        )},
        {"role": "user", "content": user_input}
    ]
    
    print("   [Inference] Generating...")
    prompt = state["pipe"].tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    
    outputs = state["pipe"](prompt)
    generated = outputs[0]["generated_text"]
    
    # Strip prompt to get just the answer
    if "<|im_start|>assistant" in generated:
        response_text = generated.split("<|im_start|>assistant")[-1].strip()
    else:
        response_text = generated[len(prompt):].strip()

    return {"response": response_text}

if __name__ == "__main__":
    uvicorn.run("web_server:app", host="127.0.0.1", port=5000)