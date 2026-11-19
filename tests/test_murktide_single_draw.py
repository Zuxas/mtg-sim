"""Murktide's match APL: a cantrip draws what the card says, once.

The engine handlers draw for Preordain and Expressive Iteration; the APL drew
one more card by hand after every cantrip.

Run: python tests/test_murktide_single_draw.py
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.deck import load_deck_from_file
from engine.game_state import GameState
from apl.murktide_match import MurktideMatchAPL

DECK, _ = load_deck_from_file("decks/dimir_murktide_modern.txt")
LAND = next(c.name for c in DECK if c.is_land())


def _card(name):
    return copy.copy(next(c for c in DECK if c.name == name))


def _cards_taken_from_library(cantrip):
    gs = GameState(mainboard=[], on_play=True)
    opp = GameState(mainboard=[], on_play=False)
    gs._match_opp, opp._match_opp = opp, gs
    gs.turn = 2
    gs.land_played = True
    gs.mana_pool.add("U", 1)
    gs.mana_pool.add("R", 1)
    gs.zones.hand = [_card(cantrip)]
    gs.zones.library = [_card(LAND) for _ in range(10)]
    MurktideMatchAPL().main_phase_match(gs, opp)
    assert not any(c.name == cantrip for c in gs.zones.hand), f"{cantrip} was not cast"
    return 10 - len(gs.zones.library)


def test_preordain_draws_one():
    assert _cards_taken_from_library("Preordain") == 1


def test_expressive_iteration_looks_at_three():
    # Look at the top three: one to hand, one to the bottom, one exiled to
    # play this turn. Three cards leave the top of the library, not four.
    assert _cards_taken_from_library("Expressive Iteration") == 3


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_murktide_single_draw: OK")
