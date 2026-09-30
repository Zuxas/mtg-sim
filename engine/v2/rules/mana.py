"""Mana (CR 106.4, 605.3a) and cost payment (CR 601.2g-h). Pure."""
from __future__ import annotations

from functools import lru_cache

from engine.v2.cards import BASIC_LAND_COLOR


def land_color(state, oid) -> str:
    return BASIC_LAND_COLOR[state.definition(oid).name]


def untapped_mana_sources(state, player) -> list:
    return [oid for oid in state.battlefield()
            if state.objects[oid].controller == player and not state.objects[oid].tapped
            and state.definition(oid).is_land]


@lru_cache(maxsize=None)
def _requirements(symbols: tuple):
    """(coloured needs, generic) for a cost tuple; pure, cached. Callers must not mutate."""
    need, generic = _requirements_uncached(symbols)
    return need, generic


def _requirements_uncached(symbols):
    need, generic = {}, 0
    for sym in symbols:
        if sym.isdigit():
            generic += int(sym)
        else:
            need[sym] = need.get(sym, 0) + 1
    return need, generic


def can_pay(symbols, available: dict) -> bool:
    need, generic = _requirements(symbols)
    if any(available.get(c, 0) < n for c, n in need.items()):
        return False
    return sum(available.values()) - sum(need.values()) >= generic


def available_mana(state, player) -> dict:
    """Pool plus what every untapped mana source could add (computed once per decision)."""
    avail = dict(state.pools[player])
    for oid in untapped_mana_sources(state, player):
        c = land_color(state, oid)
        avail[c] = avail.get(c, 0) + 1
    return avail


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
