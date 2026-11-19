"""Jeskai Blink's match APL: Quantum Riddler draws one card and Teferi uses
its -3 once. Both were done by the engine handler and again by hand.

Run: python tests/test_jeskai_blink_single_etb.py
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.deck import load_deck_from_file
from engine.game_state import GameState
from apl.jeskai_blink_match import JeskaiBlinkMatchAPL

DECK, _ = load_deck_from_file("decks/jeskai_blink_modern.txt")


def _card(name):
    return copy.copy(next(c for c in DECK if c.name == name))


def _turn(hand, opp_board=()):
    gs = GameState(mainboard=[], on_play=True)
    opp = GameState(mainboard=[], on_play=False)
    gs._match_opp, opp._match_opp = opp, gs
    gs.turn = 5
    gs.land_played = True
    for colour in "WUR":
        gs.mana_pool.add(colour, 2)
    gs.zones.hand = [_card(n) for n in hand]
    gs.zones.library = [_card("Snow-Covered Plains") for _ in range(10)]
    opp.zones.battlefield = [_card(n) for n in opp_board]
    JeskaiBlinkMatchAPL().main_phase_match(gs, opp)
    return gs, opp


def test_quantum_riddler_draws_one():
    gs, _ = _turn(["Quantum Riddler"])
    assert any(c.name == "Quantum Riddler" for c in gs.zones.battlefield)
    assert len(gs.zones.library) == 9


def test_teferi_minus_three_happens_once():
    gs, opp = _turn(["Teferi, Time Raveler"], opp_board=["Ragavan, Nimble Pilferer", "Phelia, Exuberant Shepherd"])
    assert any(c.name == "Teferi, Time Raveler" for c in gs.zones.battlefield)
    assert len(opp.zones.battlefield) == 1, "one bounce, not two"
    assert len(gs.zones.library) == 9, "one card, not two"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_jeskai_blink_single_etb: OK")
