"""
gen/search.py -- Hill-climb + evolutionary optimizer over decks.

Mutation operators edit a DeckCandidate while keeping it a legal 60, then the
mana base is re-solved. hill_climb accepts a mutation only if fitness improves;
evolve runs a population with package-level crossover and records strong
card-pairs into the NotationStore.

The evaluator is injected (`evaluate_fn(cand) -> report` with a `.fitness`
attribute) so the search loop is testable offline. In production this is a thin
wrapper over gen.fitness.evaluate (which auto-generates a cached APL and
goldfishes the deck).
"""

import random

from gen.generator import split_spells_lands, rebuild_with_spells, auto_supports, assemble
from gen.package_schema import conjoin_graph
from gen.notation import NotationStore

IMPROVE_THRESHOLD = 0.5


# --- mutation operators (each returns a new candidate or None) --------------

def mut_swap_card(cand, pool, packages, rng):
    """Replace one nonland spell with another on-color simulatable card of similar cmc."""
    spells, _ = split_spells_lands(cand, pool)
    spell_names = [n for n in spells if pool.get(n) is not None]
    if not spell_names:
        return None
    victim = rng.choice(spell_names)
    vc = pool.get(victim)
    ci = set(cand.color_identity)
    cands = [c for c in pool.nonlands()
             if c.simulatable and c.name not in spells
             and set(c.color_identity).issubset(ci)
             and abs(c.cmc - vc.cmc) <= 1 and c.colored_pips]
    if not cands:
        return None
    repl = rng.choice(cands)
    new = dict(spells)
    qty = new.pop(victim)
    new[repl.name] = qty
    return rebuild_with_spells(cand, new, pool, name=cand.name)


def mut_adjust_count(cand, pool, packages, rng):
    """Shift a copy between a spell and the land count (flex slot tuning)."""
    spells, _ = split_spells_lands(cand, pool)
    names = [n for n in spells if spells[n] >= 1]
    if not names:
        return None
    name = rng.choice(names)
    delta = rng.choice([-1, 1])
    new = dict(spells)
    if delta == 1 and new[name] < 4:
        new[name] += 1            # +1 spell -> solver gives 1 fewer land
    elif delta == -1 and new[name] >= 1:
        new[name] -= 1            # -1 spell -> solver gives 1 more land
    else:
        return None
    return rebuild_with_spells(cand, new, pool, name=cand.name)


def mut_swap_support(cand, pool, packages, rng):
    """Swap a support package for a conjoins-with sibling and re-assemble."""
    if not packages:
        return None
    core = cand.packages[0]
    supports = [p for p in cand.packages[1:]]
    graph = conjoin_graph(packages)
    options = [p for p in graph.get(core, set())
               if p not in cand.packages and packages[p].role not in ("combo-core", "aggro-core")]
    if not options:
        return None
    new_support = rng.choice(options)
    if supports:
        drop = rng.choice(supports)
        new_supports = [new_support if s == drop else s for s in supports]
    else:
        new_supports = [new_support]
    try:
        return assemble(core, new_supports, pool, packages, name=cand.name,
                        lineage=cand.lineage, validate_mana=False)
    except Exception:
        return None


def mut_resolve_mana(cand, pool, packages, rng):
    """Re-solve the mana base for the current spells (no spell change)."""
    spells, _ = split_spells_lands(cand, pool)
    return rebuild_with_spells(cand, spells, pool, name=cand.name)


MUTATIONS = [mut_swap_card, mut_adjust_count, mut_swap_support, mut_resolve_mana]


# --- hill climb -------------------------------------------------------------

def hill_climb(seed, pool, packages, evaluate_fn, *, rounds=20, rng=None,
               improve_threshold=IMPROVE_THRESHOLD, lineage=None, on_step=None):
    """
    Greedy hill climb: each round apply a random mutation; keep it only if
    fitness improves by >= improve_threshold. Returns (best_cand, best_report).
    """
    rng = rng or random.Random(0)
    best = seed
    best_report = evaluate_fn(best)
    if lineage is not None:
        lineage.record(best, best_report, parent_id=None, mutation="seed")

    for r in range(rounds):
        op = rng.choice(MUTATIONS)
        child = op(best, pool, packages, rng)
        if child is None or child.main_count() != best.main_count():
            continue
        report = evaluate_fn(child)
        improved = report.fitness - best_report.fitness >= improve_threshold
        if lineage is not None:
            lineage.record(child, report, parent_id=best.lineage[-1] if best.lineage else None,
                           mutation=op.__name__)
        if improved:
            best, best_report = child, report
        if on_step:
            on_step(r, op.__name__, report.fitness, best_report.fitness, improved)
    return best, best_report


# --- evolutionary search ----------------------------------------------------

def evolve(seeds, pool, packages, evaluate_fn, *, generations=5, pop_size=8,
           rng=None, notation_store=None, lineage=None, elite=2):
    """
    Population search. Each generation: evaluate, keep elites, breed the rest via
    package crossover + mutation. Strong card-pairs in above-median decks are
    recorded to the NotationStore. Returns the best (cand, report).
    """
    rng = rng or random.Random(0)
    store = notation_store if notation_store is not None else NotationStore()
    population = list(seeds)[:pop_size]
    while len(population) < pop_size and seeds:
        population.append(seeds[rng.randrange(len(seeds))])

    best, best_report = None, None
    for gen in range(generations):
        scored = []
        for cand in population:
            rep = evaluate_fn(cand)
            scored.append((rep.fitness, cand, rep))
            if lineage is not None:
                lineage.record(cand, rep, mutation=f"gen{gen}")
            if best_report is None or rep.fitness > best_report.fitness:
                best, best_report = cand, rep
        scored.sort(key=lambda x: -x[0])

        # record notations from above-median decks
        if scored:
            median = scored[len(scored) // 2][0]
            for fitn, cand, rep in scored:
                if fitn >= median:
                    _record_notations(cand, pool, fitn - median, store, rng)

        # next generation: elites + bred children
        elites = [c for _, c, _ in scored[:elite]]
        children = []
        while len(elites) + len(children) < pop_size:
            pa = _tournament(scored, rng)
            pb = _tournament(scored, rng)
            child = _crossover(pa, pb, pool, packages, rng) or pa
            op = rng.choice(MUTATIONS)
            mutated = op(child, pool, packages, rng)
            children.append(mutated if (mutated and mutated.main_count() == 60) else child)
        population = elites + children

    return best, best_report, store


def _tournament(scored, rng, k=3):
    picks = [scored[rng.randrange(len(scored))] for _ in range(min(k, len(scored)))]
    picks.sort(key=lambda x: -x[0])
    return picks[0][1]


def _crossover(pa, pb, pool, packages, rng):
    """Combine the cores/supports of two same-identity parents into a new deck."""
    if set(pa.color_identity) != set(pb.color_identity):
        return None
    core = pa.packages[0]
    supports = list(dict.fromkeys(pa.packages[1:] + pb.packages[1:]))
    rng.shuffle(supports)
    try:
        return assemble(core, supports[:4], pool, packages, name=pa.name,
                        validate_mana=False)
    except Exception:
        return None


def _record_notations(cand, pool, weight, store, rng, max_pairs=6):
    """Sample card pairs from a deck's nonland spells into the NotationStore."""
    spells = [n for n, q in cand.mainboard.items()
              if pool.get(n) is not None and not pool.get(n).is_land]
    if len(spells) < 2:
        return
    for _ in range(min(max_pairs, len(spells))):
        a, b = rng.sample(spells, 2)
        store.record((a, b), max(0.0, weight), deck_id=cand.name)
