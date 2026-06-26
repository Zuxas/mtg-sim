"""
gen/mana_solver.py -- Mana-base solver, castability-validated.

Given a deck's nonland spells and a CardPool, produce a land base that:
  1. weights colored-source demand by quantity AND curve-earliness (an early
     {R} needs red sources more urgently than a late one), then
  2. allocates colored sources proportional to that demand, filling fixing from
     Modern-legal dual/fetch/shock lands in the pool and topping up with basics, and
  3. is validated by Monte-Carlo opening-hand castability that taps real
     engine.mana.ManaPool objects -- so the solver agrees with how the sim
     actually pays costs (incl. flex mana from duals/fetches).

Usage:
    from gen.mana_solver import solve_manabase, castability
    lands = solve_manabase(spells, pool, total_lands=24)
    score = castability(lands, spells, pool)
"""

import random

from engine.mana import ManaPool, parse_cost

BASIC_FOR_COLOR = {"W": "Plains", "U": "Island", "B": "Swamp",
                   "R": "Mountain", "G": "Forest"}

# Minimum on-curve cast rate (conditional on hitting land drops) for a mana base
# to be considered sound. Two-color bases with light fixing land near here; the
# optimizer can push higher by adding sources.
CASTABILITY_FLOOR = 0.80


def colored_demand(spells: dict, pool) -> dict:
    """Curve-weighted colored pip demand: {color: weighted_count}."""
    demand = {}
    for name, qty in spells.items():
        pc = pool.get(name)
        if pc is None or pc.is_land:
            continue
        weight = 1.6 if pc.cmc <= 2 else 1.0
        for color, n in pc.colored_pips.items():
            demand[color] = demand.get(color, 0.0) + n * qty * weight
    return demand


def _fixing_lands(colors, pool, budget):
    """Pick up to `budget` nonbasic fixing copies (duals/tris) on-color from the pool.

    Returns {land_name: qty}. Prefers broader lands; caps each nonbasic at 4.
    """
    cset = set(colors)
    cands = [l for l in pool.lands()
             if len(l.color_identity) >= 2 and set(l.color_identity).issubset(cset)]
    # broadest fixing first, then deterministic by name
    cands.sort(key=lambda l: (-len(set(l.color_identity) & cset), l.name))
    out, used = {}, 0
    for l in cands:
        if used >= budget:
            break
        take = min(4, budget - used)
        out[l.name] = take
        used += take
    return out


def solve_manabase(spells: dict, pool, total_lands: int = 24,
                   fetch_dual_budget: int = 8, utility_lands: dict = None) -> dict:
    """
    Return {land_name: qty} summing to total_lands for the given spells.

    utility_lands: optional {name: qty} of package-requested lands (counted first).
    """
    utility_lands = dict(utility_lands or {})
    demand = colored_demand(spells, pool)
    colors = sorted(demand.keys(), key=lambda c: -demand[c])

    base = {}
    remaining = total_lands

    # 1. package-requested utility/special lands, capped to budget.
    for name, qty in utility_lands.items():
        if remaining <= 0:
            break
        q = min(qty, remaining)
        base[name] = base.get(name, 0) + q
        remaining -= q

    # 0-color (artifact/colorless) deck: fill with the most relevant basic or wastes.
    if not colors:
        # default to colorless-friendly basics split arbitrarily but deterministically
        if remaining > 0:
            base["Wastes"] = base.get("Wastes", 0) + remaining if pool.get("Wastes") else 0
            if not pool.get("Wastes"):
                base["Island"] = base.get("Island", 0) + remaining
            remaining = 0
        return base

    # 2. nonbasic fixing (only meaningful for 2+ colors).
    if len(colors) >= 2 and remaining > 0:
        budget = min(fetch_dual_budget, remaining - len(colors))  # leave room for 1 basic/color
        budget = max(0, budget)
        for name, qty in _fixing_lands(colors, pool, budget).items():
            q = min(qty, remaining)
            base[name] = base.get(name, 0) + q
            remaining -= q

    # 3. colored basics proportional to demand (>=1 per color while slots remain).
    total_demand = sum(demand.values()) or 1.0
    # guarantee one of each color first
    for c in colors:
        if remaining <= 0:
            break
        basic = BASIC_FOR_COLOR.get(c)
        if basic:
            base[basic] = base.get(basic, 0) + 1
            remaining -= 1
    # distribute the rest by demand share
    if remaining > 0:
        shares = {c: demand[c] / total_demand for c in colors}
        # largest-remainder allocation for determinism
        alloc = {c: int(remaining * shares[c]) for c in colors}
        leftover = remaining - sum(alloc.values())
        for c in sorted(colors, key=lambda c: -((remaining * shares[c]) % 1)):
            if leftover <= 0:
                break
            alloc[c] += 1
            leftover -= 1
        for c, n in alloc.items():
            basic = BASIC_FOR_COLOR.get(c)
            if basic and n:
                base[basic] = base.get(basic, 0) + n
        remaining = 0

    return base


def _type_line_for_land(name, pool):
    pc = pool.get(name)
    if pc is not None:
        return pc.type_line, name
    # synthesized basics (always resolvable)
    for color, basic in BASIC_FOR_COLOR.items():
        if name == basic:
            return f"Basic Land - {basic}", name
    return "Land", name


def castability(manabase: dict, spells: dict, pool, deck_size: int = 60,
                trials: int = 2000, seed: int = 42, sample_n: int = 4) -> float:
    """
    Monte-Carlo fraction of games where the hardest early colored spells are
    castable on (or near) curve, tapping real ManaPool objects.

    Returns a value in [0,1]; the generator rejects manabases below a threshold.
    """
    # sample the most color-intensive early spells (the ones a base must support)
    samples = []
    for name, qty in spells.items():
        pc = pool.get(name)
        if pc is None or pc.is_land or not pc.colored_pips:
            continue
        intensity = sum(pc.colored_pips.values())
        samples.append((intensity, pc.cmc, name, pc.mana_cost, pc.cmc))
    if not samples:
        return 1.0
    samples.sort(key=lambda s: (-s[0], s[1]))
    samples = samples[:sample_n]

    land_tiles = []
    for name, qty in manabase.items():
        land_tiles.extend([_type_line_for_land(name, pool)] * qty)
    n_lands = len(land_tiles)
    n_spells = max(0, deck_size - n_lands)
    library_template = land_tiles + [None] * n_spells

    rng = random.Random(seed)
    worst = 1.0
    for _, cmc, name, mana_cost, _ in samples:
        turn = max(1, min(int(cmc) if cmc else 1, 6))
        need_lands = max(turn, int(cmc) if cmc else 1)
        ok = relevant = 0
        for _ in range(trials):
            lib = library_template[:]
            rng.shuffle(lib)
            draw = 7 + max(0, turn - 1)          # on the play, no T1 draw
            hand = lib[:draw]
            lands_in_hand = [t for t in hand if t is not None]
            if len(lands_in_hand) < need_lands:
                continue                          # missed land drops; not a mana-color test
            relevant += 1
            pool_obj = ManaPool()
            for type_line, lname in lands_in_hand[:max(need_lands, turn)]:
                pool_obj.add_land(type_line, lname)
            if pool_obj.can_pay(mana_cost, cmc):
                ok += 1
        rate = (ok / relevant) if relevant else 1.0
        worst = min(worst, rate)
    return worst
