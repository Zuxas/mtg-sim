"""Private library decisions (milestone four, S3). Pure.

- scry N (CR 701.22a): "look at the top N cards of your library, then put any number of them on the
  bottom of your library in any order and the rest on top of your library in any order."
- surveil N (CR 701.25a): "...put any number of them into your graveyard and the rest on top of
  your library in any order." (The graveyard is ordered, CR 404.2, so that order is chosen too.)
- iterate (Expressive Iteration): "Look at the top three cards of your library. Put one of them into
  your hand, put one of them on the bottom of your library, and exile one of them. You may play the
  exiled card this turn." With fewer cards the instructions are followed in the order given for the
  cards that are there (card ruling; CR 609.3).
Scry 0 / surveil 0 is no event (CR 701.22b / 701.25c): with an empty library nothing is looked at.

A decision is a placement: top (new top card first), bottom (in the order they are put there),
graveyard (in order), hand, exile. Every legal placement is enumerated (complete action set).
"""
from __future__ import annotations

from itertools import combinations, permutations
from typing import NamedTuple


class Placement(NamedTuple):
    top: tuple = ()
    bottom: tuple = ()
    graveyard: tuple = ()
    hand: tuple = ()
    exile: tuple = ()


def _split_orders(cards, other_field):
    """Every (top order, other order) partition with both parts in every order."""
    out = []
    n = len(cards)
    for k in range(n + 1):
        for rest in combinations(cards, k):
            top = [c for c in cards if c not in rest]
            for t in permutations(top):
                for r in permutations(rest):
                    out.append(Placement(**{"top": t, other_field: r}))
    return out


def placements(kind, cards) -> list:
    cards = tuple(cards)
    if not cards:
        return [Placement()]
    if kind == "scry":
        return _split_orders(cards, "bottom")
    if kind == "surveil":
        return _split_orders(cards, "graveyard")
    if kind == "iterate":
        out = []
        for perm in permutations(cards):
            hand, bottom, exile = perm[:1], perm[1:2], perm[2:3]
            out.append(Placement(hand=hand, bottom=bottom, exile=exile))
        return sorted(set(out))
    raise ValueError(kind)


def valid(kind, cards, pl) -> bool:
    return pl in placements(kind, cards)


# What each library-looking spell / ability does around its decision: (ops before, kind, N, ops after).
# The pre / post entries are op names applied to the controller (only "draw" is needed).
LIBRARY = {
    "preordain": ((), "scry", 2, ("draw",)),                 # "Scry 2, then draw a card."
    "serum_visions": (("draw",), "scry", 2, ()),             # "Draw a card. Scry 2."
    "expressive_iteration": ((), "iterate", 3, ()),
    "drc_surveil": ((), "surveil", 1, ()),                   # Dragon's Rage Channeler trigger
    "falls_surveil": ((), "surveil", 1, ()),                 # Thundering Falls ETB trigger
}
