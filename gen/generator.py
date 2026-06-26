"""
gen/generator.py -- Assemble synergy packages into a legal decklist.

Takes a core package plus compatible support packages (selected explicitly or
auto-chosen by following conjoins_with edges), merges their cards, curve-fills
or trims to a spell budget, solves the mana base (gen/mana_solver.py), and emits
a DeckCandidate that loads as exactly `target_size` mainboard cards.

A candidate is flagged low-fidelity if any load-bearing (nonland) card is not
simulatable -- the engine cannot pilot it faithfully, so downstream scoring
caps its verdict.

Usage:
    from gen.generator import assemble, auto_supports
    cand = assemble("amulet_titan_core", ["green_ramp_engine", "amulet_bounce_lands"],
                    pool, packages)
"""

from dataclasses import dataclass, field, asdict

from gen.mana_solver import solve_manabase, castability, CASTABILITY_FLOOR
from gen.package_schema import conjoin_graph

# Trim support packages before cores; cores are the deck's reason to exist.
_TRIM_PRIORITY = {"payoff": 0, "interaction": 1, "mana": 2, "engine": 3,
                  "aggro-core": 9, "combo-core": 9}


@dataclass
class DeckCandidate:
    name: str
    mainboard: dict
    sideboard: dict = field(default_factory=dict)
    packages: list = field(default_factory=list)
    color_identity: list = field(default_factory=list)
    lineage: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def main_count(self):
        return sum(self.mainboard.values())

    def spell_count(self, pool):
        return sum(q for n, q in self.mainboard.items()
                   if (pool.get(n) is None or not pool.get(n).is_land))

    def land_count(self, pool):
        return self.main_count() - self.spell_count(pool)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


def auto_supports(core_id, packages, max_supports=4):
    """Pick support packages reachable from the core via conjoins_with, on-color."""
    graph = conjoin_graph(packages)
    core = packages[core_id]
    core_ci = set(core.color_identity)
    reachable = graph.get(core_id, set())
    cands = []
    for pid in reachable:
        pkg = packages[pid]
        if pid == core_id or pkg.role in ("combo-core", "aggro-core"):
            continue
        # only widen identity by at most one extra color
        widened = core_ci | set(pkg.color_identity)
        if len(widened) <= max(2, len(core_ci) + 1):
            cands.append((pid, pkg))
    # prefer mana + engine first, then interaction/payoff; deterministic
    order = {"mana": 0, "engine": 1, "interaction": 2, "payoff": 3}
    cands.sort(key=lambda x: (order.get(x[1].role, 9), x[0]))
    return [pid for pid, _ in cands[:max_supports]]


def _merge_cards(pkg_ids, packages):
    merged = {}
    for pid in pkg_ids:
        for name, qty in packages[pid].cards.items():
            merged[name] = merged.get(name, 0) + qty
    # MTG legality: max 4 copies of a non-basic card
    for name in merged:
        merged[name] = min(merged[name], 4)
    return merged


def _split_lands(cards, pool):
    spells, lands = {}, {}
    for name, qty in cards.items():
        pc = pool.get(name)
        if pc is not None and pc.is_land:
            lands[name] = qty
        else:
            spells[name] = qty
    return spells, lands


def _target_lands(spells, pool):
    """Heuristic land count from average mana value (ramp wants more, aggro fewer)."""
    total_cmc = total_qty = 0
    for name, qty in spells.items():
        pc = pool.get(name)
        if pc is None:
            continue
        total_cmc += pc.cmc * qty
        total_qty += qty
    avg = (total_cmc / total_qty) if total_qty else 2.0
    return max(17, min(26, round(14 + 2.0 * avg)))


def _filler(spells, color_identity, pool, want):
    """On-color, simulatable, low-curve filler to reach the spell budget."""
    have = set(spells)
    ci = set(color_identity)
    cands = [c for c in pool.nonlands()
             if c.simulatable and c.name not in have
             and set(c.color_identity).issubset(ci) and c.colored_pips]
    cands.sort(key=lambda c: (c.cmc, c.name))
    added = {}
    for c in cands:
        if want <= 0:
            break
        take = min(4, want)
        added[c.name] = take
        want -= take
    return added


def _trim(spells, packages, pkg_ids, pool, excess):
    """Remove `excess` spell copies, lowest-priority packages first."""
    # map card -> lowest trim priority among packages that include it
    card_prio = {}
    for pid in pkg_ids:
        pr = _TRIM_PRIORITY.get(packages[pid].role, 5)
        for name in packages[pid].cards:
            card_prio[name] = min(card_prio.get(name, 99), pr)
    order = sorted(spells.keys(), key=lambda n: (card_prio.get(n, 5), -spells[n], n))
    out = dict(spells)
    for name in order:
        while excess > 0 and out.get(name, 0) > 0:
            out[name] -= 1
            excess -= 1
            if out[name] == 0:
                del out[name]
        if excess <= 0:
            break
    return out


def assemble(core_id, support_ids, pool, packages, target_size=60,
             name=None, lineage=None, validate_mana=True):
    """Build a DeckCandidate from a core + support packages."""
    pkg_ids = [core_id] + [s for s in support_ids if s != core_id]
    merged = _merge_cards(pkg_ids, packages)
    spells, pkg_lands = _split_lands(merged, pool)

    color_identity = sorted(set().union(*[set(packages[p].color_identity) for p in pkg_ids]))

    target_lands = _target_lands(spells, pool)
    spell_budget = target_size - target_lands

    s = sum(spells.values())
    if s > spell_budget:
        spells = _trim(spells, packages, pkg_ids, pool, s - spell_budget)
    elif s < spell_budget:
        spells.update(_filler(spells, color_identity, pool, spell_budget - sum(spells.values())))
        # filler may overshoot in 4-of chunks; trim back to exact budget
        s2 = sum(spells.values())
        if s2 > spell_budget:
            spells = _trim(spells, packages, pkg_ids, pool, s2 - spell_budget)

    spell_total = sum(spells.values())
    lands_needed = target_size - spell_total
    manabase = solve_manabase(spells, pool, total_lands=lands_needed,
                              utility_lands=pkg_lands)

    mainboard = dict(spells)
    for name_, qty in manabase.items():
        mainboard[name_] = mainboard.get(name_, 0) + qty

    # fidelity check on load-bearing nonland cards
    unsim = [n for n in spells if pool.get(n) is not None and not pool.get(n).simulatable]
    fidelity = "low" if unsim else "high"

    meta = {
        "target_lands": target_lands,
        "fidelity": fidelity,
        "unsimulatable_cards": unsim,
    }
    if validate_mana:
        cast = castability(manabase, spells, pool)
        meta["castability"] = round(cast, 3)
        meta["mana_ok"] = cast >= CASTABILITY_FLOOR

    return DeckCandidate(
        name=name or f"{core_id}+{'+'.join(support_ids)}",
        mainboard=mainboard,
        sideboard={},
        packages=pkg_ids,
        color_identity=color_identity,
        lineage=list(lineage or []),
        metadata=meta,
    )


def split_spells_lands(cand, pool):
    """Split a candidate mainboard into (spells, lands) dicts."""
    return _split_lands(cand.mainboard, pool)


def rebuild_with_spells(cand, spells, pool, target_size=60, validate_mana=False,
                        name=None, lineage=None):
    """
    Rebuild a candidate from an edited spell list, re-solving the mana base to
    keep exactly `target_size` cards. Preserves packages / color identity; used
    by the optimizer's mutation operators.
    """
    spells = {n: q for n, q in spells.items() if q > 0}
    spell_total = sum(spells.values())
    lands_needed = max(0, target_size - spell_total)
    manabase = solve_manabase(spells, pool, total_lands=lands_needed)

    mainboard = dict(spells)
    for n, q in manabase.items():
        mainboard[n] = mainboard.get(n, 0) + q

    unsim = [n for n in spells if pool.get(n) is not None and not pool.get(n).simulatable]
    meta = dict(cand.metadata)
    meta["fidelity"] = "low" if unsim else "high"
    meta["unsimulatable_cards"] = unsim
    if validate_mana:
        cast = castability(manabase, spells, pool)
        meta["castability"] = round(cast, 3)
        meta["mana_ok"] = cast >= CASTABILITY_FLOOR

    return DeckCandidate(
        name=name or cand.name,
        mainboard=mainboard,
        sideboard=dict(cand.sideboard),
        packages=list(cand.packages),
        color_identity=list(cand.color_identity),
        lineage=list(lineage if lineage is not None else cand.lineage),
        metadata=meta,
    )


def generate(pool, packages, *, core_id, support_ids=None, seed=0, **kw):
    """Convenience: assemble with auto-selected supports when none are given."""
    if support_ids is None:
        support_ids = auto_supports(core_id, packages)
    return assemble(core_id, support_ids, pool, packages, **kw)
