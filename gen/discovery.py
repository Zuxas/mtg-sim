"""
gen/discovery.py -- Archetype discovery: mine strong packages, propose novel decks.

Two capabilities:
  mine_packages()      -- promote card subsets that repeatedly co-occur in
                          high-fitness decks (via the NotationStore) into NEW
                          Package objects, flagged with a machine provenance for
                          human review before they become seeds.
  propose_archetypes() -- walk the conjoins_with graph (biased by notation
                          strength) to assemble core+support combinations that
                          have NOT been piloted together, handing them back to
                          the optimizer as fresh seeds -> new archetypes.
"""

from gen.package_schema import Package, conjoin_graph
from gen.generator import assemble


def _components(pairs):
    """Union-find over (a,b) edges -> list of connected card sets."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    for a, b in pairs:
        union(a, b)
    comps = {}
    for node in list(parent):
        comps.setdefault(find(node), set()).add(node)
    return list(comps.values())


def mine_packages(notation_store, pool, *, min_strength=1.0, min_observations=2,
                  min_size=2, max_size=6, run_id="run"):
    """
    Build candidate Packages from strong, repeatedly-observed card combinations.
    Returns a list of Package objects (provenance 'discovered:<run_id>').
    """
    edges = []
    for nt in notation_store.top(n=1000, min_observations=min_observations):
        if nt.strength >= min_strength and len(nt.cards) >= 2:
            cs = list(nt.cards)
            for i in range(len(cs)):
                for j in range(i + 1, len(cs)):
                    edges.append((cs[i], cs[j]))
    if not edges:
        return []

    out = []
    for idx, comp in enumerate(_components(edges)):
        comp = [c for c in comp if pool.get(c) is not None]
        if not (min_size <= len(comp) <= max_size):
            continue
        ci = set()
        simulatable = True
        cards = {}
        for name in sorted(comp):
            pc = pool.get(name)
            ci |= set(pc.color_identity)
            simulatable = simulatable and pc.simulatable
            # creatures tend to want full sets; spells fewer
            cards[name] = 4 if "creature" in pc.type_line.lower() else 3
        pid = f"discovered_{run_id}_{idx}"
        n = sum(cards.values())
        out.append(Package(
            id=pid, name=f"Discovered cluster {idx} ({run_id})", role="engine",
            cards=cards, color_identity=sorted(ci),
            conjoins_with=[], tags=["discovered"],
            synergy_notes="Auto-mined: these cards co-occurred in high-fitness decks.",
            provenance=f"discovered:{run_id}", min_slots=n, max_slots=n,
            requires_simulatable=simulatable,
        ))
    return out


def propose_archetypes(packages, pool, *, notation_store=None, seen_sets=None,
                       max_proposals=6):
    """
    Assemble novel core+support combinations not present in `seen_sets` (a set of
    frozenset(package_ids) already piloted). Returns a list of DeckCandidates.
    """
    seen_sets = set(seen_sets or set())
    graph = conjoin_graph(packages)
    cores = [pid for pid, p in packages.items() if p.role in ("combo-core", "aggro-core")]

    # strength bias: how strongly a support is implicated by notations
    def support_weight(support_id):
        if notation_store is None:
            return 0.0
        pkg = packages[support_id]
        cands = notation_store.conjoin_candidates(pkg, limit=50)
        return sum(c.strength for c in cands)

    proposals = []
    for core in sorted(cores):
        core_ci = set(packages[core].color_identity)
        supports = [s for s in graph.get(core, set())
                    if packages[s].role not in ("combo-core", "aggro-core")
                    and len(core_ci | set(packages[s].color_identity)) <= len(core_ci) + 1]
        supports.sort(key=lambda s: (-support_weight(s), s))
        # try progressively larger novel support sets
        for k in (1, 2, 3):
            chosen = supports[:k]
            if not chosen:
                continue
            pkg_set = frozenset([core] + chosen)
            if pkg_set in seen_sets:
                continue
            try:
                cand = assemble(core, chosen, pool, packages,
                                name=f"discover_{core}_{'_'.join(chosen)}",
                                validate_mana=False)
            except Exception:
                continue
            cand.metadata["provenance"] = "discovered:archetype"
            proposals.append(cand)
            seen_sets.add(pkg_set)
            if len(proposals) >= max_proposals:
                return proposals
    return proposals
