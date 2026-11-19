"""Affinity match APL: Emry, Lurker of the Loch mills four cards, not eight.

The engine handler mills four as Emry enters; the APL milled four more.

Run: python tests/test_affinity_single_emry_mill.py
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.deck import load_deck_from_file
from engine.game_state import GameState
from apl.affinity_match import IzzetAffinityMatchAPL, EMRY

DECK, _ = load_deck_from_file("decks/izzet_affinity_modern.txt")
LAND = next(c.name for c in DECK if c.is_land())


def _card(name):
    return copy.copy(next(c for c in DECK if c.name == name))


def test_emry_mills_four():
    gs = GameState(mainboard=[], on_play=True)
    opp = GameState(mainboard=[], on_play=False)
    gs._match_opp, opp._match_opp = opp, gs
    gs.turn = 3
    gs.land_played = True
    gs.mana_pool.add("U", 3)
    gs.zones.hand = [_card(EMRY)]
    gs.zones.library = [_card(LAND) for _ in range(12)]
    IzzetAffinityMatchAPL().main_phase_match(gs, opp)
    assert any(c.name == EMRY for c in gs.zones.battlefield), "Emry was not cast"
    assert len(gs.zones.library) == 8, len(gs.zones.library)
    assert len(gs.zones.graveyard) == 4, len(gs.zones.graveyard)


if __name__ == "__main__":
    test_emry_mills_four()
    print("test_affinity_single_emry_mill: OK")
