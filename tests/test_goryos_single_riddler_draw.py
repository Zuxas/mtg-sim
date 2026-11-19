"""Goryo's match APL: a hard-cast Quantum Riddler draws one card.

The engine handler draws it; the APL drew another by hand.

Run: python tests/test_goryos_single_riddler_draw.py
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.deck import load_deck_from_file
from engine.game_state import GameState
from apl.goryos_match import GoryosMatchAPL, QUANTUM

DECK, _ = load_deck_from_file("decks/goryos_vengeance_modern.txt")
LAND = next(c.name for c in DECK if c.is_land())


def _card(name):
    return copy.copy(next(c for c in DECK if c.name == name))


def test_riddler_draws_one():
    gs = GameState(mainboard=[], on_play=True)
    opp = GameState(mainboard=[], on_play=False)
    gs._match_opp, opp._match_opp = opp, gs
    gs.turn = 5
    gs.land_played = True
    gs.mana_pool.add("U", 5)
    gs.zones.hand = [_card(QUANTUM), _card(LAND), _card(LAND)]   # not on its <=1 card static
    gs.zones.library = [_card(LAND) for _ in range(10)]
    GoryosMatchAPL().main_phase_match(gs, opp)
    assert any(c.name == QUANTUM for c in gs.zones.battlefield), "Riddler was not cast"
    assert len(gs.zones.library) == 9, len(gs.zones.library)


if __name__ == "__main__":
    test_riddler_draws_one()
    print("test_goryos_single_riddler_draw: OK")
