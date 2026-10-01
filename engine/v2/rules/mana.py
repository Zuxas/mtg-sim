"""Mana (CR 106.4, 305.6, 605) and cost payment (CR 601.2g-h). Pure.

A land's mana abilities come from its basic land types (CR 305.6: intrinsic "{T}: Add [mana]")
and from the card's own mana-ability text (MANA_ABILITIES, keyed by effect key). Each option is
(colour, life cost); a life cost is payable only with at least that much life (CR 119.4).
Castability uses exact source-to-colour matching: a source that can add one of several colours
adds exactly ONE mana, so dual lands are never double counted.
"""
from __future__ import annotations

from functools import lru_cache
from typing import NamedTuple

from engine.v2.cards import BASIC_LAND_COLOR

# effect_key -> (colours, life cost) of the card's printed mana ability ("{T}[, Pay N life]: Add X or Y")
MANA_ABILITIES = {
    "sunbaked_canyon": (("R", "W"), 1),
    "fiery_islet": (("U", "R"), 1),
    "inspiring_vantage": (("R", "W"), 0),
}


_OPTS: dict = {}                     # card name -> options (definitions are fixed per name)


def _options_for(definition) -> tuple:
    opts = []
    for sub in definition.subtypes:                                     # CR 305.6 intrinsic abilities
        if sub in BASIC_LAND_COLOR:
            opts.append((BASIC_LAND_COLOR[sub], 0))
    printed = MANA_ABILITIES.get(definition.effect_key)
    if printed:
        colours, life = printed
        opts += [(c, life) for c in colours]
    seen, out = set(), []
    for o in opts:
        if o not in seen:
            seen.add(o)
            out.append(o)
    return tuple(out)


def _opts_of(d) -> tuple:
    opts = _OPTS.get(d.name)
    if opts is None:
        opts = _OPTS[d.name] = _options_for(d) if d.is_land else ()
    return opts


def mana_options(state, oid) -> tuple:
    """((colour, life_cost), ...) this permanent's mana abilities can produce."""
    return _opts_of(state.def_by_ciid[state.objects[oid].ciid])


def _affordable(opts, life) -> tuple:
    if all(l <= life for _c, l in opts):                               # common case: nothing filtered
        return opts
    return tuple((c, l) for c, l in opts if life >= l)


def activatable_mana_options(state, player, oid) -> tuple:
    return _affordable(mana_options(state, oid), state.life[player])


def sources_with_options(state, player) -> list:
    """[(oid, activatable options)] for the player's untapped mana sources (one pass)."""
    life = state.life[player]
    objs, cache = state.objects, state.mana_by_ciid
    out = []
    for oid in state.zones[("bf",)]:
        o = objs[oid]
        if o.controller != player or o.tapped:
            continue
        opts = cache.get(o.ciid)
        if opts is None:                                               # derived from the fixed definition
            opts = cache[o.ciid] = _opts_of(state.def_by_ciid[o.ciid])
        if opts:
            opts = _affordable(opts, life)
            if opts:
                out.append((oid, opts))
    return out


def untapped_mana_sources(state, player) -> list:
    return [oid for oid, _o in sources_with_options(state, player)]


class Avail(NamedTuple):
    pool: dict                       # colour -> mana already in the pool
    sources: tuple                   # per untapped mana source: its ((colour, life_cost), ...) options;
                                     # each source adds ONE mana
    life: int = 0                    # life available for mana-ability life costs (CR 119.4: the total
                                     # paid can't exceed it; paying down to exactly 0 is allowed)


@lru_cache(maxsize=None)
def _requirements(symbols: tuple):
    """(coloured needs, generic) for a cost tuple; pure, cached. Callers must not mutate."""
    need, generic = {}, 0
    for sym in symbols:
        if sym.isdigit():
            generic += int(sym)
        else:
            need[sym] = need.get(sym, 0) + 1
    return need, generic


def available_mana(state, player) -> Avail:
    """Pool plus what every untapped mana source could add (computed once per decision)."""
    return avail_from(state, player, sources_with_options(state, player))


def avail_from(state, player, srcs):
    """Avail for can_pay. When every source has exactly one free option (basic lands), the
    matching problem reduces to counting, so a plain colour->amount dict is returned (same answer)."""
    if all(len(opts) == 1 and opts[0][1] == 0 for _oid, opts in srcs):
        avail = dict(state.pools[player])
        for _oid, ((c, _l),) in srcs:
            avail[c] = avail.get(c, 0) + 1
        return avail
    return Avail(dict(state.pools[player]), tuple(opts for _oid, opts in srcs), state.life[player])


def can_pay(symbols, avail) -> bool:
    need, generic = _requirements(symbols)
    if isinstance(avail, dict):                                        # pool only
        if any(avail.get(c, 0) < n for c, n in need.items()):
            return False
        return sum(avail.values()) - sum(need.values()) >= generic
    pool = dict(avail.pool)
    left = []
    for c, n in need.items():                                          # pool first (never worse)
        use = min(n, pool.get(c, 0))
        pool[c] = pool.get(c, 0) - use
        left += [c] * (n - use)
    srcs = avail.sources
    if len(left) > len(srcs):
        return False
    spare_pool = sum(pool.values())

    def generic_ok(used, budget) -> bool:
        if generic <= spare_pool:
            return True
        n = spare_pool
        for c in sorted(min(l for _c, l in srcs[j]) for j in range(len(srcs)) if j not in used):
            if c <= budget:                                            # cheapest life costs first
                n += 1
                budget -= c
        return n >= generic

    def match(i, used, budget):
        if i == len(left):
            return generic_ok(used, budget)
        want = left[i]
        for j, opts in enumerate(srcs):
            if j in used:
                continue
            cost = min((l for c, l in opts if c == want), default=None)
            if cost is not None and cost <= budget and match(i + 1, used | {j}, budget - cost):
                return True
        return False
    return match(0, frozenset(), avail.life)


def payable_with_sources(state, player, symbols, avail=None, life=0) -> bool:
    """Can `symbols` be paid from the pool plus untapped sources while also paying `life` (a life
    component of the announced cost, e.g. Phyrexian mana paid with life)? CR 119.4 / 118.3: the
    life must be there when it is paid, and mana abilities with life costs share the same budget."""
    avail = available_mana(state, player) if avail is None else avail
    if life:
        if isinstance(avail, dict):                                    # no life-cost sources in this case
            if state.life[player] < life:
                return False
        else:
            if avail.life < life:
                return False
            avail = avail._replace(life=avail.life - life)
    return can_pay(symbols, avail)


PHYREXIAN_LIFE = 2                                                     # CR 107.4f


@lru_cache(maxsize=None)
def mana_variants(symbols: tuple) -> tuple:
    """The ways to announce a mana cost (CR 107.4f, 601.2b/f): each Phyrexian symbol "{X/P}" is paid
    either with one X or with 2 life, chosen when the cost is determined. Returns
    ((name, mana symbols, life), ...): "normal" pays every Phyrexian symbol with mana;
    "phyrexian:<colours>" pays the listed Phyrexian symbols with life."""
    plain = tuple(x for x in symbols if not x.endswith("/P"))
    phy = sorted(x[:-2] for x in symbols if x.endswith("/P"))
    if not phy:
        return (("normal", tuple(symbols), 0),)
    out, seen = [], set()
    from itertools import combinations
    for k in range(len(phy) + 1):
        for idx in combinations(range(len(phy)), k):
            life_cols = tuple(phy[i] for i in idx)
            if life_cols in seen:
                continue
            seen.add(life_cols)
            rest = list(phy)
            for c in life_cols:
                rest.remove(c)
            name = "normal" if not life_cols else "phyrexian:" + "".join(life_cols)
            out.append((name, plain + tuple(rest), PHYREXIAN_LIFE * len(life_cols)))
    return tuple(out)


def payment_assignments(symbols, pool: dict) -> list:
    """Every distinct way to pay `symbols` from `pool` (mana of one type is interchangeable --
    mana is not an object, so this enumeration is exact). Returns sorted ((colour, n), ...)."""
    need, generic = _requirements(symbols)
    remaining = dict(pool)
    for c, n in need.items():
        if remaining.get(c, 0) < n:
            return []
        remaining[c] -= n
    colours = sorted(c for c, n in remaining.items() if n > 0)
    out = []

    def rec(i, left, chosen):
        if left == 0:
            spend = dict(need)
            for c, n in chosen.items():
                spend[c] = spend.get(c, 0) + n
            out.append(tuple(sorted((c, n) for c, n in spend.items() if n)))
            return
        if i >= len(colours):
            return
        c = colours[i]
        for k in range(min(left, remaining[c]), -1, -1):
            if k:
                chosen[c] = k
            rec(i + 1, left - k, chosen)
            chosen.pop(c, None)

    rec(0, generic, {})
    return sorted(set(out))
