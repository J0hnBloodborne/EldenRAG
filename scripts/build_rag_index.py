import argparse
import json
import os
import time
from collections import defaultdict

import torch
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS
from sentence_transformers import SentenceTransformer


PREDICATE_LABELS = {
    # Common RDF / OWL
    "rdf:type": "type",
    "rdfs:label": "label",
    "rdfs:comment": "description",
    "owl:sameAs": "same as",

    # Elden Ring ontology predicates (humanize for better retrieval)
    "er:scalesWith": "scales with",
    "er:isUpgradeOf": "is upgrade of",
    "er:droppedBy": "dropped by",
    "er:drops": "drops",
    "er:dropsItem": "drops item",
    "er:hasBoss": "has boss",
    "er:hasNPC": "has NPC",
    "er:hasCreature": "has creature",
    "er:unlocksRecipeFor": "unlocks recipe for",
    "er:unlocksAffinity": "unlocks affinity",
    "er:hasWeight": "weight",
    "er:gameId": "game id",
}


def _best_local_name(uri: str) -> str:
    uri = uri.rstrip("/>")
    if "#" in uri:
        return uri.split("#")[-1]
    return uri.split("/")[-1]


def _graph_stats(path: str) -> dict:
    st = os.stat(path)
    return {
        "path": path.replace("\\", "/"),
        "mtime": int(st.st_mtime),
        "size": int(st.st_size),
    }


def _load_graph(graph_path: str) -> Graph:
    g = Graph()
    ext = os.path.splitext(graph_path)[1].lower()
    if ext == ".ttl":
        fmt = "turtle"
    elif ext == ".nt":
        fmt = "nt"
    else:
        fmt = None

    start = time.time()
    g.parse(graph_path, format=fmt)
    print(f"Loaded {len(g):,} triples from {graph_path} in {time.time() - start:.2f}s")
    return g


def _build_label_map(g: Graph) -> dict[URIRef, str]:
    labels: dict[URIRef, str] = {}
    for s, o in g.subject_objects(RDFS.label):
        if isinstance(s, URIRef) and isinstance(o, Literal) and s not in labels:
            labels[s] = str(o)
    return labels


def _term_to_text(g: Graph, labels: dict[URIRef, str], term) -> str:
    if isinstance(term, Literal):
        return str(term)
    if isinstance(term, URIRef):
        if term in labels:
            return labels[term]
        try:
            # Prefer QName-like output if bound
            return g.namespace_manager.normalizeUri(term)
        except Exception:
            return _best_local_name(str(term))
    return str(term)


def _predicate_to_text(g: Graph, labels: dict[URIRef, str], pred: URIRef) -> str:
    if pred in (RDF.type,):
        return "type"
    if pred == RDFS.label:
        return "label"
    if pred == RDFS.comment:
        return "description"

    try:
        qname = g.namespace_manager.normalizeUri(pred)
        if qname in PREDICATE_LABELS:
            return PREDICATE_LABELS[qname]
    except Exception:
        qname = None

    return _term_to_text(g, labels, pred)


def build_entity_documents(g: Graph) -> list[dict]:
    labels = _build_label_map(g)

    comments: dict[URIRef, str] = {}
    for s, o in g.subject_objects(RDFS.comment):
        if isinstance(s, URIRef) and isinstance(o, Literal) and s not in comments:
            comments[s] = str(o)

    by_subject: dict[URIRef, list[tuple[URIRef, object]]] = defaultdict(list)
    for s, p, o in g:
        if isinstance(s, URIRef):
            by_subject[s].append((p, o))

    docs: list[dict] = []
    for s, triples in by_subject.items():
        title = labels.get(s) or _best_local_name(str(s)).replace("_", " ")
        description = comments.get(s)

        lines: list[str] = []
        if description:
            lines.append(f"Description: {description}")

        # Sort for determinism
        triples_sorted = sorted(triples, key=lambda t: (str(t[0]), str(t[1])))
        for p, o in triples_sorted:
            if p in (RDFS.label, RDFS.comment):
                continue
            p_txt = _predicate_to_text(g, labels, p)
            o_txt = _term_to_text(g, labels, o)
            lines.append(f"{p_txt}: {o_txt}")

        text = title
        if lines:
            text = title + "\n" + "\n".join(lines)

        docs.append(
            {
                "subject": str(s),
                "title": title,
                "text": text,
            }
        )

    print(f"Built {len(docs):,} entity documents")
    return docs


def embed_and_save(
    docs: list[dict],
    out_dir: str,
    retriever_id: str,
    graph_info: dict,
    batch_size: int,
) -> None:
    os.makedirs(out_dir, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading retriever {retriever_id} on {device}...")
    bi = SentenceTransformer(retriever_id, device=device)

    texts = [d["text"] for d in docs]
    start = time.time()
    embeddings = bi.encode(
        texts,
        convert_to_tensor=True,
        show_progress_bar=True,
        batch_size=batch_size,
        normalize_embeddings=True,
    )
    print(f"Embedded {len(texts):,} docs in {time.time() - start:.2f}s")

    docs_path = os.path.join(out_dir, "docs.json")
    emb_path = os.path.join(out_dir, "embeddings.pt")
    meta_path = os.path.join(out_dir, "meta.json")

    with open(docs_path, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False)

    # Save on CPU for portability; server can move to GPU at runtime.
    torch.save(embeddings.detach().cpu(), emb_path)

    meta = {
        "created_at": int(time.time()),
        "retriever_id": retriever_id,
        "embedding_dim": int(embeddings.shape[1]),
        "doc_count": int(len(docs)),
        "graph": graph_info,
        "cuda_available": bool(torch.cuda.is_available()),
        "torch_version": torch.__version__,
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Wrote {docs_path}")
    print(f"Wrote {emb_path}")
    print(f"Wrote {meta_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a persisted RAG index from Elden Ring RDF.")
    parser.add_argument(
        "--graph",
        default="rdf/elden_ring_fast_linked.nt",
        help="Path to RDF graph (.ttl or .nt). Default: rdf/elden_ring_fast_linked.nt",
    )
    parser.add_argument(
        "--out",
        default="rag_index",
        help="Output directory for docs/embeddings/meta. Default: rag_index",
    )
    parser.add_argument(
        "--retriever",
        default="all-MiniLM-L6-v2",
        help="SentenceTransformer model id. Default: all-MiniLM-L6-v2",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Embedding batch size. Default: 64",
    )
    args = parser.parse_args()

    graph_path = args.graph
    if not os.path.exists(graph_path):
        raise FileNotFoundError(
            f"Graph not found: {graph_path}. Make sure you generated rdf/elden_ring_linked.ttl and scripts/optimize.py output first."
        )

    g = _load_graph(graph_path)
    docs = build_entity_documents(g)
    embed_and_save(
        docs=docs,
        out_dir=args.out,
        retriever_id=args.retriever,
        graph_info=_graph_stats(graph_path),
        batch_size=args.batch_size,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
