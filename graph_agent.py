import rdflib
from rdflib import Graph, URIRef, Literal
import re

# ---------------------------------------------------------
# 1. SETUP & LOADING DATA
# ---------------------------------------------------------
print("Loading Knowledge Graph... (this may take a few seconds)")
g = Graph()
g.parse("rdf/elden_ring_optimized.ttl", format="turtle")
print(f"Graph Loaded! {len(g)} facts available.")

# Namespace map for cleaner output
NS = {
    "er": "http://www.semanticweb.org/fall2025/eldenring/",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "schema1": "http://schema.org/"
}

# Pre-load all labels for fast entity linking
# format: {"malenia": "http://.../Malenia", "moonveil": "http://.../Moonveil"}
ENTITY_INDEX = {}
for s, p, o in g.triples((None, URIRef(NS["rdfs"] + "label"), None)):
    if isinstance(o, Literal):
        name_key = str(o).lower()
        ENTITY_INDEX[name_key] = s

# ---------------------------------------------------------
# 2. THE RETRIEVAL ENGINE (NO LLM REQUIRED HERE)
# ---------------------------------------------------------
def get_entity_neighborhood(entity_uri):
    """
    Fetches the 'Context Subgraph' for an entity.
    This solves the 'er:hasMaxStats' issue and the 'Lore Connection' issue automatically.
    """
    facts = []
    
    # A. Get direct properties (Name, Description, Location, Image)
    for s, p, o in g.triples((entity_uri, None, None)):
        prop_name = p.split("/")[-1].split("#")[-1]
        
        # CLEANUP: Skip boring RDF types if we have many
        if prop_name == "type": continue 
        
        # HANDLE STATS: If we hit 'hasMaxStats', dive deeper!
        if prop_name == "hasMaxStats":
            stats_node = o
            facts.append("  [Gameplay Stats]:")
            for _, stat_p, stat_o in g.triples((stats_node, None, None)):
                stat_name = stat_p.split("/")[-1]
                facts.append(f"    - {stat_name}: {stat_o}")
        else:
            val = o.split("/")[-1] if isinstance(o, URIRef) else str(o)
            facts.append(f"  - {prop_name}: {val}")

    # B. Get Incoming Connections (What mentions this?)
    # This is CRITICAL for Lore. "Who talks about Miquella?"
    mentions = list(g.subjects(URIRef(NS["er"] + "mentions"), entity_uri))
    if mentions:
        facts.append("\n  [Mentioned By / Connected To]:")
        for m in mentions[:10]: # Limit to 10 to fit context
            # Get the name of the thing mentioning it
            label = g.value(m, URIRef(NS["rdfs"] + "label"))
            if label:
                facts.append(f"    - {label}")
                # Optional: Get the description of the item mentioning it
                desc = g.value(m, URIRef(NS["rdfs"] + "comment"))
                if desc:
                    # Truncate long descriptions
                    facts.append(f"      (Quote: \"{str(desc)[:100]}...\")")

    return "\n".join(facts)

def find_entities_in_query(query):
    """
    Simple keyword matching to find which Graph Nodes the user is asking about.
    """
    found_uris = []
    query_lower = query.lower()
    
    # Sort by length to match "Malenia, Blade of Miquella" before "Malenia"
    sorted_keys = sorted(ENTITY_INDEX.keys(), key=len, reverse=True)
    
    for name in sorted_keys:
        if name in query_lower:
            found_uris.append((name, ENTITY_INDEX[name]))
            # Remove found name from query to avoid double matching substrings
            query_lower = query_lower.replace(name, "")
            
    return found_uris

# ---------------------------------------------------------
# 3. THE "AGENT" INTERFACE
# ---------------------------------------------------------
# NOTE: In a real app, you would import your LLM here (Ollama, OpenAI, HuggingFace)
# For this script, I will simulate the "Prompt Construction" so you can see exactly
# what gets fed to the LLM.

def run_agent_query(user_query):
    print(f"\n{'='*60}")
    print(f"USER ASKED: \"{user_query}\"")
    print(f"{'='*60}")
    
    # 1. Identify Subject
    entities = find_entities_in_query(user_query)
    
    if not entities:
        print(">> AGENT: I couldn't find any specific game entities (Bosses, Items, NPCs) in your question.")
        print(">> TRY: asking about 'Moonveil', 'Malenia', or 'Carian Slicer'.")
        return

    # 2. Retrieve Context (The "Graph RAG" part)
    context_data = ""
    print(f">> AGENT: I detected {len(entities)} entities. Fetching subgraphs...")
    
    for name, uri in entities:
        print(f"   -> Fetching neighborhood for: {name} ({uri.split('/')[-1]})")
        data = get_entity_neighborhood(uri)
        context_data += f"\n--- DATA FOR: {name.upper()} ---\n{data}\n"

    # 3. Construct the Prompt (This is what you send to your LLM)
    system_prompt = f"""
    You are an Elden Ring Knowledge Agent.
    Answer the user's question primarily using the KNOWLEDGE GRAPH DATA provided below.
    
    If the user asks about Lore, look at the "Mentioned By" section and "comments".
    If the user asks about Stats, look at the "Gameplay Stats" section.
    
    ### KNOWLEDGE GRAPH DATA ###
    {context_data}
    
    ### USER QUESTION ###
    {user_query}
    """
    
    # 4. (Simulation) In your `web_server.py`, this `system_prompt` goes into `pipe(prompt)`
    print("\n" + "-"*20 + " GENERATED PROMPT CONTEXT " + "-"*20)
    print(context_data)
    print("-" * 60)
    print(">> READY TO GENERATE ANSWER. (Hook this string into your LLM!)")

# ---------------------------------------------------------
# 4. INTERACTIVE LOOP
# ---------------------------------------------------------
if __name__ == "__main__":
    print("\n--- ELDEN RING GRAPH AGENT (Reasoning Mode) ---")
    print("Type a question (e.g., 'What scales with the Moonveil?' or 'Who is connected to Miquella?')")
    print("Type 'quit' to exit.")
    
    while True:
        q = input("\nQuery: ")
        if q.lower() in ["quit", "exit"]: break
        run_agent_query(q)