"""
OWL RL Reasoning Stage
======================
Runs a real Description Logic reasoner (OWL 2 RL profile, via owlrl) over the
knowledge graph. This replaces the hand-written inference in optimize.py with an
actual reasoner that:

  1. VALIDATES consistency  -- catches disjointness / datatype violations that the
     manual rules in optimize.py silently ignore.
  2. MATERIALIZES inferences from the ontology axioms -- union classes (Equippable),
     intersection classes (HolyWeapon), transitive properties (locatedIn+), class
     hierarchy, inverse and symmetric properties, etc.
  3. CLEANS the closure -- OWL RL emits a lot of scaffolding (reflexive owl:sameAs,
     rdf:type owl:Thing on everything, internal bookkeeping). We strip it so the
     output stays a usable graph rather than tripling in size with noise.

Run AFTER optimize.py:
    python scripts/reasoner.py
Output: rdf/elden_ring_reasoned.ttl
"""
import sys
import time
from rdflib import Graph, Namespace, RDF, RDFS, OWL
import owlrl

ER = Namespace("http://www.semanticweb.org/fall2025/eldenring/")

SCHEMA_FILE = "rdf/elden_ring_schema.ttl"
DATA_FILE   = "rdf/elden_ring_optimized.ttl"
OUTPUT_FILE = "rdf/elden_ring_reasoned.ttl"

# owlrl marks a detected inconsistency by asserting membership in this class, and
# emits validation problems typed as this DAML ErrorMessage class.
ERROR_MESSAGE = "http://www.daml.org/2002/03/agents/agent-ont#ErrorMessage"


def local(uri):
    s = str(uri)
    return s.rsplit("#", 1)[-1] if "#" in s else s.rsplit("/", 1)[-1]


def load_graph():
    g = Graph()
    print(f"1. Loading schema : {SCHEMA_FILE}")
    g.parse(SCHEMA_FILE, format="turtle")
    print(f"2. Loading data   : {DATA_FILE}")
    t = time.time()
    g.parse(DATA_FILE, format="turtle")
    print(f"   [Loaded] {len(g)} triples in {time.time() - t:.1f}s")
    return g


def collect_errors(g):
    """Return (inconsistency_individuals, error_messages) found in the closure."""
    nothing = [s for s in g.subjects(RDF.type, OWL.Nothing)]
    errors = []
    for node in g.subjects(RDF.type, OWL.Class):  # cheap no-op to keep signature stable
        break
    for s, _, o in g.triples((None, RDF.type, None)):
        if str(o) == ERROR_MESSAGE:
            msg = g.value(s, OWL.members) or next(
                (mo for mp, mo in g.predicate_objects(s) if "error" in str(mp).lower()),
                None,
            )
            if msg is not None:
                errors.append(str(msg))
    return nothing, errors


def clean_closure(g):
    """Strip reasoner scaffolding that adds size but no value."""
    removed = 0

    # Reflexive owl:sameAs (x sameAs x) -- always emitted, never useful.
    for s, o in list(g.subject_objects(OWL.sameAs)):
        if s == o:
            g.remove((s, OWL.sameAs, o))
            removed += 1

    # rdf:type owl:Thing on every individual -- pure noise for our use.
    for s in list(g.subjects(RDF.type, OWL.Thing)):
        g.remove((s, RDF.type, OWL.Thing))
        removed += 1

    # The DAML ErrorMessage scaffolding (only present if validation found problems;
    # we surface those separately and refuse to serialize a broken graph anyway).
    for s in list(g.subjects()):
        for _, o in list(g.predicate_objects(s)):
            if str(o) == ERROR_MESSAGE:
                for p2, o2 in list(g.predicate_objects(s)):
                    g.remove((s, p2, o2))
                    removed += 1
    return removed


def report_inferences(g):
    """Print counts of the interesting materialized inferences."""
    def count_type(cls):
        return len(set(g.subjects(RDF.type, cls)))

    print("\n--- Materialized inferences (highlights) ---")
    print(f"   Equippable (union Weapon/Armor/Talisman/Shield): {count_type(ER.Equippable)}")
    print(f"   HolyWeapon (Weapon INTERSECT requiresFaith)     : {count_type(ER.HolyWeapon)}")
    print(f"   PeacefulEntity (complement of Boss)             : {count_type(ER.PeacefulEntity)}")
    loc_edges = len(list(g.subject_objects(ER.locatedIn)))
    print(f"   locatedIn edges (incl. transitive closure)      : {loc_edges}")
    dropped = len(list(g.subject_objects(ER.droppedBy)))
    print(f"   droppedBy edges (inverse of drops)              : {dropped}")


def main():
    print("--- STARTING OWL RL REASONING STAGE ---")
    g = load_graph()
    before = len(g)

    print("\n3. Running OWL RL reasoner (owlrl DeductiveClosure)...")
    t = time.time()
    owlrl.DeductiveClosure(
        owlrl.OWLRL_Semantics,
        axiomatic_triples=False,
        datatype_axioms=True,
    ).expand(g)
    print(f"   [Done] closure computed in {time.time() - t:.1f}s ({len(g)} triples)")

    # 4. Consistency / validation gate.
    print("\n4. Checking consistency...")
    nothing, errors = collect_errors(g)
    if nothing or errors:
        print("   [FAIL] Ontology is INCONSISTENT. Not writing output.")
        for ind in nothing[:20]:
            print(f"      owl:Nothing -> {local(ind)}")
        for msg in errors[:20]:
            print(f"      ERROR -> {msg}")
        sys.exit(1)
    print("   [OK] Consistent. No contradictions, no datatype violations.")

    # 5. Clean and report.
    removed = clean_closure(g)
    print(f"\n5. Cleaned {removed} scaffolding triples from the closure.")
    report_inferences(g)

    print(f"\n6. Saving to {OUTPUT_FILE}...")
    g.serialize(destination=OUTPUT_FILE, format="turtle")
    inferred = len(g) - before
    print(f"--- DONE. {len(g)} triples ({'+' if inferred >= 0 else ''}{inferred} vs input) ---")


if __name__ == "__main__":
    main()
