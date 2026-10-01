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


@lru_cache(maxsize=None)
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


def mana_options(state, oid) -> tuple:
    """((colour, life_cost), ...) this permanent's mana abilities can produce."""
    d = state.definition(oid)
    return _options_for(d) if d.is_land else ()


def activatable_mana_options(state, player, oid) -> tuple:
    return tuple((c, life) for c, life in mana_options(state, oid) if state.life[player] >= life)


def untapped_mana_sources(state, player) -> list:
    out = []
    for oid in state.battlefield():
        o = state.objects[oid]
        if o.controller == player and not o.tapped and activatable_mana_options(state, player, oid):
            out.append(oid)
    return out


class Avail(NamedTuple):
    pool: dict                       # colour -> mana already in the pool
    sources: tuple                   # frozenset of colours per untapped mana source (each adds ONE mana)


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
    srcs = tuple(frozenset(c for c, _l in activatable_mana_options(state, player, oid))
                 for oid in untapped_mana_sources(state, player))
    return Avail(dict(state.pools[player]), srcs)


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

    def match(i, used):
        if i == len(left):
            return spare_pool + len(srcs) - len(used) >= generic
        for j, cols in enumerate(srcs):
            if j not in used and left[i] in cols:
                if match(i + 1, used | {j}):
                    return True
        return False
    return match(0, frozenset())


def payable_with_sources(state, player, symbols, avail=None) -> bool:
    return can_pay(symbols, available_mana(state, player) if avail is None else avail)


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
