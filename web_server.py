import uvicorn
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
import json
import time
import torch
from rdflib import Graph
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from sentence_transformers import SentenceTransformer, CrossEncoder, util

app = FastAPI(title="EldenRAG Final", description="Precision Reranking")

# --- CONFIG ---
GRAPH_FILE = "rdf/elden_ring_fast_linked.nt"
INDEX_DIR = "rag_index"
DOCS_PATH = os.path.join(INDEX_DIR, "docs.json")
EMB_PATH = os.path.join(INDEX_DIR, "embeddings.pt")
META_PATH = os.path.join(INDEX_DIR, "meta.json")

RETRIEVER_ID = "all-MiniLM-L6-v2"
RERANKER_ID = "cross-encoder/ms-marco-MiniLM-L-6-v2"
LLM_ID = "microsoft/Phi-3-mini-4k-instruct"

templates = Jinja2Templates(directory="templates")

class QueryModel(BaseModel):
    query: str


def _device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def _load_index():
    if not (os.path.exists(DOCS_PATH) and os.path.exists(EMB_PATH)):
        raise FileNotFoundError(
            f"Missing RAG index. Build it first with: "
            f"python scripts/build_rag_index.py --graph {GRAPH_FILE} --out {INDEX_DIR}"
        )

    with open(DOCS_PATH, "r", encoding="utf-8") as f:
        docs = json.load(f)

    embeddings = torch.load(EMB_PATH, map_location="cpu")
    if not torch.is_tensor(embeddings):
        embeddings = torch.tensor(embeddings)

    # Map doc index -> subject URI for traceability
    doc_subjects = [d.get("subject", "") for d in docs]
    doc_texts = [d.get("text", "") for d in docs]
    return docs, doc_texts, doc_subjects, embeddings


def _load_rdf_graph(graph_path: str) -> Graph:
    if not os.path.exists(graph_path):
        raise FileNotFoundError(f"RDF graph not found: {graph_path}")
    g = Graph()
    start = time.time()
    g.parse(graph_path, format="nt")
    print(f"Loaded RDF graph ({len(g):,} triples) from {graph_path} in {time.time() - start:.2f}s")
    return g


# --- Load retrieval assets once (fast) ---
print("⏳ Loading RAG index + models...")
print(f"   Torch CUDA available: {torch.cuda.is_available()}")

docs, doc_texts, doc_subjects, corpus_embeddings_cpu = _load_index()

# Load RDF graph once so certain questions can be answered exactly via SPARQL.
rdf_graph = _load_rdf_graph(GRAPH_FILE)

print(f"Loading Bi-Encoder ({RETRIEVER_ID}) on {_device()}...")
bi_encoder = SentenceTransformer(RETRIEVER_ID, device=_device())

print(f"Loading Cross-Encoder ({RERANKER_ID}) on {_device()}...")
cross_encoder = CrossEncoder(RERANKER_ID, device=_device())

corpus_embeddings = corpus_embeddings_cpu.to(_device())
print(f"Index ready: {len(doc_texts):,} docs, dim={corpus_embeddings.shape[1]}")

try:
    tokenizer = AutoTokenizer.from_pretrained(LLM_ID)
    model = AutoModelForCausalLM.from_pretrained(
        LLM_ID,
        device_map="auto",
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )
    # Work around occasional transformers/model cache API mismatches for Phi-3.
    # Disabling cache is slower but avoids runtime errors like DynamicCache missing attributes.
    try:
        model.generation_config.use_cache = False
    except Exception:
        pass
    llm_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=256)
    print("Phi-3 Ready.")
except Exception as e:
    print(f"LLM Error: {e}")
    llm_pipeline = None

# --- 3. RETRIEVAL LOGIC ---
def _extract_stats(lower_q: str) -> list[str]:
    stats = []
    if "str" in lower_q or "strength" in lower_q:
        stats.append("Strength")
    if "int" in lower_q or "intelligence" in lower_q:
        stats.append("Intelligence")
    if "dex" in lower_q or "dexterity" in lower_q:
        stats.append("Dexterity")
    if "fth" in lower_q or "faith" in lower_q:
        stats.append("Faith")
    if "arc" in lower_q or "arcane" in lower_q:
        stats.append("Arcane")
    return stats


def structured_retrieve(user_query: str) -> str | None:
    """Return grounded context from RDF for question types we can answer exactly."""
    lower_q = user_query.lower()

    # Weapon scaling questions: answer from KG so we don't retrieve upgrade variants.
    if "weapon" in lower_q and "scale" in lower_q:
        stats = _extract_stats(lower_q)
        if len(stats) >= 2:
            a, b = stats[0], stats[1]
            sparql = f"""
            PREFIX er: <http://www.semanticweb.org/fall2025/eldenring/>
            PREFIX attribute: <http://www.semanticweb.org/fall2025/eldenring/Attribute/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT DISTINCT ?label WHERE {{
              ?w a er:Weapon ;
                 er:scalesWith attribute:{a} ;
                 er:scalesWith attribute:{b} ;
                 rdfs:label ?label .
            }}
            LIMIT 50
            """
            try:
                rows = list(rdf_graph.query(sparql))
            except Exception as e:
                print(f"SPARQL Error: {e}")
                return None

            if not rows:
                return None

            labels = sorted({str(r[0]) for r in rows})
            bullets = "\n".join([f"- {x}" for x in labels[:25]])
            return f"Weapons that scale with both {a} and {b}:\n{bullets}"

    return None


def retrieve_and_rerank(user_query):
    print(f"\nProcessing Query: '{user_query}'")
    lower_q = user_query.lower()
    
    # 1. PARSE STATS
    required_stats = _extract_stats(lower_q)

    # 2. STANDARD SEMANTIC SEARCH
    query_embedding = bi_encoder.encode(user_query, convert_to_tensor=True, normalize_embeddings=True)
    hits = util.semantic_search(query_embedding, corpus_embeddings, top_k=200 if len(required_stats) > 1 else 50)[0]

    # 3. OPTIONAL DUAL-STAT FILTER
    # The old approach used intersection of two synthetic searches, which often returns 0.
    # Instead, we retrieve normally and then filter candidates by presence of both stats tokens.
    if len(required_stats) > 1 and hits:
        print(f"   Detected Dual-Stat Request: {required_stats}")
        want_tokens = []
        for stat in required_stats:
            want_tokens.append(f"attribute:{stat}")
            want_tokens.append(stat)

        filtered = []
        for hit in hits:
            text = doc_texts[hit['corpus_id']]
            if all((tok in text) for tok in want_tokens[0:2:2]):
                # Prefer the stricter attribute:Stat match if present
                filtered.append(hit)
            elif all((stat in text) for stat in required_stats):
                filtered.append(hit)

        if filtered:
            print(f"   Filtered to {len(filtered)} dual-stat candidates.")
            hits = filtered
        else:
            print("   No strict dual-stat matches; falling back to semantic search results.")

    if not hits:
        return None

    # 3. RERANKING
    cross_inp = [[user_query, doc_texts[hit['corpus_id']]] for hit in hits]
    cross_scores = cross_encoder.predict(cross_inp)
    
    for idx in range(len(cross_scores)):
        hits[idx]['cross_score'] = cross_scores[idx]
        
    hits = sorted(hits, key=lambda x: x['cross_score'], reverse=True)
    
    results = []
    seen_names = set()
    
    for hit in hits:
        score = hit['cross_score']
        content = doc_texts[hit['corpus_id']]
        name = docs[hit['corpus_id']].get("title") or content.split("\n", 1)[0]
        
        # Heuristic: If asking for weapon, ignore Seals/Staffs
        if "weapon" in lower_q and ("Seal" in name or "Staff" in name):
            continue
            
        # Lowered Threshold to -4.0 to guarantee debug output
        if score > -4.0 and name not in seen_names:
            print(f"   MATCH ({score:.2f}): {name}") # Log to terminal
            results.append(content)
            seen_names.add(name)
            
        if len(results) >= 5: break

    # Fallback: if reranker scores are all low, still return top-N hits.
    if not results:
        for hit in hits[:5]:
            content = doc_texts[hit['corpus_id']]
            results.append(content)

    if not results:
        return None
    return "\n\n".join(results)

def generate_answer(context, query):
    if not llm_pipeline: return "LLM not loaded."
    
    messages = [
        {"role": "user", "content": f"You are Melina. Use the Data Context to answer. Be concise. If listing items, use bullet points.\n\nData Context:\n{context}\n\nQuestion: {query}"}
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    try:
        outputs = llm_pipeline(
            prompt,
            do_sample=True,
            temperature=0.1,
            top_p=0.9,
            # Avoid Phi-3 cache API mismatch errors on some transformers versions.
            use_cache=False,
        )
        return outputs[0]["generated_text"].split("<|assistant|>")[-1].strip()
    except Exception as e:
        # Never hard-fail the API route on generation; return grounded context instead.
        print(f"LLM Generation Error: {e}")
        return (
            "I couldn't generate a full response due to an LLM runtime error. "
            "Here is the most relevant context I found:\n\n" + context
        )

# --- ROUTES ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat")
async def chat(request: QueryModel):
    context = structured_retrieve(request.query) or retrieve_and_rerank(request.query)
    if not context:
        return {"context": "No data found.", "response": "The Archives are silent on this matter."}
    
    ai_response = generate_answer(context, request.query)
    return {"context": context, "response": ai_response}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)