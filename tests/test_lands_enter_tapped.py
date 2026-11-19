"""A land that enters tapped gives no mana the turn it is played.

The engine knew this for about 60 lands by name. Another 47 in decks/ (surveil
lands, Triomes, creature lands, bounce lands, Bojuka Bog...) were tapped for
mana at once. The rule is now read from the card's text.

Run: python tests/test_lands_enter_tapped.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from engine.game_state import GameState

ALWAYS = "{T}: Add {U} or {R}.\n%s enters tapped.\nWhen %s enters, surveil 1."
SLOW = "%s enters tapped unless you control two or more other lands.\n{T}: Add {B} or {G}."
CREATURE_LAND = "If you control two or more other lands, %s enters tapped.\n{T}: Add {U}."
CASTLE = "%s enters tapped unless you control a Swamp.\n{T}: Add {B}."
VERGE_LIKE = "%s enters tapped unless you control a Plains or an Island.\n{T}: Add {R}."
BASIC_CHECK = "%s enters tapped unless you control a basic land.\n{T}: Add {C}."
SHOCK = "As %s enters, you may pay 2 life. If you don't, it enters tapped."


def _land(name, text="", type_line="Land"):
    c = Card(name=name, mana_cost="", cmc=0.0, type_line=type_line,
             oracle_text=text.replace("%s", name))
    c.tags = {Tag.LAND}
    return c


def _tapped(card, *board):
    gs = GameState(mainboard=[], on_play=True)
    gs.zones.battlefield.extend(board)
    gs.zones.battlefield.append(card)
    return gs._enters_tapped(card)


MOUNTAIN = lambda: _land("Mountain", type_line="Basic Land - Mountain")
PLAINS = lambda: _land("Plains", type_line="Basic Land - Plains")
SWAMP_DUAL = lambda: _land("Test Mortuary", type_line="Land - Swamp Plains")


def test_unconditional():
    assert _tapped(_land("Test Falls", ALWAYS, "Land - Island Mountain"))
    assert _tapped(_land("Test Bog", "Test Bog enters the battlefield tapped.\n{T}: Add {B}."))


def test_untapped_lands_stay_untapped():
    assert not _tapped(MOUNTAIN())
    assert not _tapped(_land("Test Tarn", "{T}, Pay 1 life, Sacrifice Test Tarn: Search..."))
    assert not _tapped(_land("Test Shock", SHOCK, "Land - Mountain Plains"))   # pays 2 life


def test_slow_land():
    assert _tapped(_land("Test Glade", SLOW))
    assert _tapped(_land("Test Glade", SLOW), MOUNTAIN())
    assert not _tapped(_land("Test Glade", SLOW), MOUNTAIN(), PLAINS())


def test_creature_land_is_the_other_way_round():
    assert not _tapped(_land("Test Hall", CREATURE_LAND))
    assert _tapped(_land("Test Hall", CREATURE_LAND), MOUNTAIN(), PLAINS())


def test_unless_you_control_a_land_type():
    assert _tapped(_land("Test Castle", CASTLE))
    assert _tapped(_land("Test Castle", CASTLE), MOUNTAIN())
    assert not _tapped(_land("Test Castle", CASTLE), SWAMP_DUAL())
    assert _tapped(_land("Test Monastery", VERGE_LIKE), MOUNTAIN())
    assert not _tapped(_land("Test Monastery", VERGE_LIKE), PLAINS())
    assert _tapped(_land("Test Temple", BASIC_CHECK), SWAMP_DUAL())
    assert not _tapped(_land("Test Temple", BASIC_CHECK), MOUNTAIN())


def test_playing_a_tapped_land_adds_no_mana():
    gs = GameState(mainboard=[], on_play=True)
    falls = _land("Test Falls", ALWAYS, "Land - Island Mountain")
    gs.zones.hand.append(falls)
    assert gs.play_land(falls)
    assert gs.mana_pool.total() == 0 and falls.tapped


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_lands_enter_tapped: OK")
