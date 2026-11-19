"""Card handlers must change a zone's list in place, never replace it.

match_runner hands each phase a GameState view whose zone lists ARE the match
state's lists. A handler that did `gs.zones.library = gs.zones.library[4:]`
only replaced the view's list: the match state kept the milled cards in the
library while they also went to the graveyard. Cards were duplicated, and a
creature returned from the graveyard and cast was on the battlefield and still
in its owner's library. 19 handlers did this.

Run: python tests/test_handlers_mutate_zones_in_place.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from data.card import Card, Tag
from engine.game_state import GameState
from engine.card_handlers_verified import _overlord_balemurk_etb


def _card(name, type_line="Creature - Test"):
    c = Card(name=name, mana_cost="{1}", cmc=1.0, type_line=type_line)
    c.tags = {Tag.CREATURE}
    return c


def test_mill_shrinks_the_shared_library():
    shared_library = [_card(f"Card {i}") for i in range(10)]
    view = GameState(mainboard=[], on_play=True)
    view.zones.library = shared_library            # what match_runner does
    _overlord_balemurk_etb(view, _card("Overlord of the Balemurk", "Creature - Avatar Horror"))
    assert view.zones.library is shared_library, "the handler replaced the list"
    assert len(shared_library) == 6, "the match state still holds the milled cards"
    moved = view.zones.graveyard + view.zones.hand
    assert len(moved) == 4 and not any(c in shared_library for c in moved)


def test_no_handler_rebinds_a_zone_list():
    pattern = re.compile(
        r"^\s*\w+\.zones\.(library|hand|graveyard|battlefield)\s*=\s*\w+(\.zones\.\w+)?\[", re.M)
    for rel in ("engine/card_handlers_verified.py", "engine/card_effects.py",
                "engine/standard_auto_handlers.py", "engine/effect_primitives.py"):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            hits = pattern.findall(f.read())
        assert not hits, f"{rel}: {len(hits)} handler(s) replace a zone list with a slice"


if __name__ == "__main__":
    test_mill_shrinks_the_shared_library()
    test_no_handler_rebinds_a_zone_list()
    print("test_handlers_mutate_zones_in_place: OK")
