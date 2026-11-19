"""Esper Blink's match APL: each effect once, and no crash.

The APL repeated by hand what the engine handlers already do: Quantum
Riddler's draw, Teferi's -3 and Solitude's exile after an Ephemerate blink.
The second removal crashed when the handler had already taken the target
(11 of 60 mirror games).

Run: python tests/test_esper_blink_single_etb.py
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.deck import load_deck_from_file
from engine.game_state import GameState
from engine import match_engine
from apl.esper_blink_match import EsperBlinkMatchAPL

DECK, _ = load_deck_from_file("decks/esper_blink_modern.txt")
LAND = next(c.name for c in DECK if c.is_land())


def _card(name):
    return copy.copy(next(c for c in DECK if c.name == name))


def _turn(board, hand, opp_board):
    gs = GameState(mainboard=[], on_play=True)
    opp = GameState(mainboard=[], on_play=False)
    gs._match_opp, opp._match_opp = opp, gs
    gs.turn = 5
    gs.land_played = True
    for colour in "WUB":
        gs.mana_pool.add(colour, 2)
    for name in board:
        c = _card(name)
        c.summoning_sickness = False
        gs.zones.battlefield.append(c)
    gs.zones.hand = [_card(n) for n in hand]
    gs.zones.library = [_card(LAND) for _ in range(10)]
    opp.zones.battlefield = [_card(n) for n in opp_board]
    EsperBlinkMatchAPL().main_phase_match(gs, opp)
    return gs, opp


def test_quantum_riddler_draws_one():
    gs, _ = _turn([], ["Quantum Riddler"], [])
    assert len(gs.zones.library) == 9


def test_teferi_minus_three_happens_once():
    gs, opp = _turn([], ["Teferi, Time Raveler"], ["Solitude", "Solitude"])
    assert len(opp.zones.battlefield) == 1 and len(gs.zones.library) == 9


def test_ephemerate_on_solitude_exiles_one_creature():
    _, opp = _turn(["Solitude"], ["Ephemerate"], ["Solitude", "Solitude"])
    assert len(opp.zones.battlefield) == 1 and len(opp.zones.exile) == 1


def test_mirror_games_do_not_crash():
    for seed in range(40):
        match_engine.run_match(EsperBlinkMatchAPL(), DECK, EsperBlinkMatchAPL(), DECK, seed=seed)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_esper_blink_single_etb: OK")
