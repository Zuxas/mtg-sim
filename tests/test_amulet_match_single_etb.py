"""Amulet Titan's MATCH APL: Spelunking and Arboreal Grazer resolve once.

The engine handlers draw Spelunking's card and put the land onto the
battlefield for both cards; the match APL did it again by hand, so Spelunking
drew two and ramped two and Grazer ramped two. (The goldfish APL,
apl/amulet_titan.py, is separate and untouched.)

Run: python tests/test_amulet_match_single_etb.py
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.deck import load_deck_from_file
from engine.game_state import GameState
from apl.amulet_titan_match import AmuletTitanMatchAPL

DECK, _ = load_deck_from_file("decks/amulet_titan_modern.txt")


def _card(name):
    return copy.copy(next(c for c in DECK if c.name == name))


def _turn(spell):
    gs = GameState(mainboard=[], on_play=True)
    opp = GameState(mainboard=[], on_play=False)
    gs._match_opp, opp._match_opp = opp, gs
    gs.turn = 3
    gs.land_played = True                       # the turn's land drop is used
    gs.mana_pool.add("G", 3)
    gs.zones.hand = [_card(spell)] + [_card("Forest") for _ in range(3)]
    gs.zones.library = [_card("Forest") for _ in range(10)]
    AmuletTitanMatchAPL().main_phase_match(gs, opp)
    lands = sum(1 for c in gs.zones.battlefield if c.is_land())
    return lands, 10 - len(gs.zones.library)


def test_spelunking_draws_one_and_ramps_one():
    lands, drawn = _turn("Spelunking")
    assert (lands, drawn) == (1, 1), (lands, drawn)


def test_arboreal_grazer_ramps_one():
    lands, drawn = _turn("Arboreal Grazer")
    assert (lands, drawn) == (1, 0), (lands, drawn)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_amulet_match_single_etb: OK")
