"""Yawgmoth's match APL: Malevolent Rumble looks at four cards, once.

The engine handler reveals four, takes a permanent, bins the rest and makes
the Eldrazi Spawn. The APL then did the reveal-and-take again by hand on the
next four cards.

Run: python tests/test_yawgmoth_single_rumble.py
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.deck import load_deck_from_file
from engine.game_state import GameState
from apl.yawgmoth_match import YawgmothMatchAPL, MALEVOLENT

DECK, _ = load_deck_from_file("decks/yawgmoth_modern.txt")
LAND = next(c.name for c in DECK if c.is_land() and "Forest" in (c.type_line or ""))


def _card(name):
    return copy.copy(next(c for c in DECK if c.name == name))


def test_rumble_takes_four_cards_off_the_top():
    gs = GameState(mainboard=[], on_play=True)
    opp = GameState(mainboard=[], on_play=False)
    gs._match_opp, opp._match_opp = opp, gs
    gs.turn = 2
    gs.land_played = True
    gs.mana_pool.add("G", 2)
    gs.zones.hand = [_card(MALEVOLENT)]
    creature = next(c.name for c in DECK if c.cmc >= 4 and not c.is_land()
                    and "Creature" in (c.type_line or ""))
    # A creature sits fifth from the top: out of Rumble's reach.
    gs.zones.library = ([_card(LAND) for _ in range(4)] + [_card(creature)]
                        + [_card(LAND) for _ in range(7)])
    YawgmothMatchAPL().main_phase_match(gs, opp)
    assert not any(c.name == MALEVOLENT for c in gs.zones.hand), "Rumble was not cast"
    assert len(gs.zones.library) == 8, len(gs.zones.library)
    assert sum(1 for c in gs.zones.hand if c.name == LAND) == 1, "one card to hand"
    assert gs.zones.library[0].name == creature, "the fifth card was not touched"


if __name__ == "__main__":
    test_rumble_takes_four_cards_off_the_top()
    print("test_yawgmoth_single_rumble: OK")
