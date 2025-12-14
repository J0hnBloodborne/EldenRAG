import uvicorn
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
import torch
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

app = FastAPI(title="EldenRAG Generalized", description="TF-IDF Retrieval")

# --- CONFIG ---
GRAPH_FILE = "rdf/elden_ring_fast.nt"
MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
TOP_K_RETRIEVAL = 15  # How many facts to feed the LLM

# --- 1. LOAD & INDEX DATA (The "Reading" Part) ---
print("Reading Knowledge Graph and building Index...")
knowledge_base = []

if os.path.exists(GRAPH_FILE):
    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        # We clean the triples to make them "searchable text"
        # <http.../Moonveil> <http.../scalesWith> <http.../Int>  -->  "Moonveil scalesWith Int"
        for line in f:
            clean_line = line.replace("<", "").replace(">", "").replace(" .", "").strip()
            # Remove the long URL prefixes to save tokens
            clean_line = clean_line.replace("http://www.semanticweb.org/fall2025/eldenring/Attribute/", "")
            clean_line = clean_line.replace("http://www.semanticweb.org/fall2025/eldenring/", "")
            clean_line = clean_line.replace("http://www.w3.org/2000/01/rdf-schema#", "")
            knowledge_base.append(clean_line)
    print(f"Indexed {len(knowledge_base)} facts.")
else:
    print(f"Warning: {GRAPH_FILE} not found.")
    knowledge_base = ["Elden Ring is a game."] # Fallback

# Build the Search Engine (TF-IDF Vectorizer)
vectorizer = TfidfVectorizer(stop_words='english')
tfidf_matrix = vectorizer.fit_transform(knowledge_base)

# --- 2. LOAD LLM ---
print(f"Loading {MODEL_ID}...")
try:
    llm_pipeline = pipeline(
        "text-generation", 
        model=MODEL_ID, 
        device_map="cpu", # Using CPU to avoid your CUDA errors
        max_new_tokens=256
    )
    print("LLM Ready.")
except Exception as e:
    print(f"LLM Error: {e}")
    llm_pipeline = None

templates = Jinja2Templates(directory="templates")

class QueryModel(BaseModel):
    query: str

# --- GENERALIZED RETRIEVAL ---
def retrieve_knowledge(user_query: str):
    # 1. Convert user query to vector
    query_vec = vectorizer.transform([user_query])
    
    # 2. Compare against all 50,000 facts (Cosine Similarity)
    similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    
    # 3. Get Top K matches
    top_indices = similarities.argsort()[-TOP_K_RETRIEVAL:][::-1]
    
    results = []
    for idx in top_indices:
        if similarities[idx] > 0.1: # Only include if somewhat relevant
            results.append(knowledge_base[idx])
            
    if not results:
        return "No high-confidence data found in the Archives."
        
    return "\n".join(results)

def query_local_llm(context, query):
    if not llm_pipeline: return "LLM not active."
    
    # We instruct the LLM to use the retrieved facts
    messages = [
        {"role": "system", "content": "You are a helpful Elden Ring assistant. Answer the question using ONLY the provided Data context."},
        {"role": "user", "content": f"Data Context:\n{context}\n\nQuestion: {query}"}
    ]
    
    prompt = llm_pipeline.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    outputs = llm_pipeline(prompt, do_sample=True, temperature=0.7, top_k=50, top_p=0.95)
    return outputs[0]["generated_text"].split("<|assistant|>")[-1].strip()

# --- ROUTES ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat")
async def chat(request: QueryModel):
    # Step 1: Retrieve relevant facts (Generalized)
    context = retrieve_knowledge(request.query)
    
    # Step 2: Generate Answer
    ai_response = query_local_llm(context, request.query)
    
    return {"context": context, "response": ai_response}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)