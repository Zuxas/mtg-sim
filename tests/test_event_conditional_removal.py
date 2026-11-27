"""Event-conditional removal spells must gate their big mode on the event,
not assume it always happened.

- Searing Blaze deals 1/1, and 3/3 only on Landfall (a land entered under our
  control this turn). It used to hardcode 3/3. (#119)
- Fatal Push destroys CMC<=2, and CMC<=4 only on Revolt. Revolt is not tracked
  yet (no central leave-the-battlefield hook), so the conservative fix uses the
  base CMC<=2 -- it must never kill a 3-4 MV creature. (#118)

Run: python tests/test_event_conditional_removal.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from engine.game_state import GameState
from engine.card_handlers_verified import _searing_blaze_spell, _fatal_push_spell
from engine.card_effects import on_landfall


def _creature(name, cmc, toughness, power=1):
    c = Card(name=name, mana_cost="{1}", cmc=float(cmc),
             type_line="Creature - Test", power=str(power), toughness=str(toughness))
    c.tags = {Tag.CREATURE}
    c.counters = 0
    return c


def _caster_with_opp():
    me = GameState(mainboard=[], on_play=True)
    opp = GameState(mainboard=[], on_play=False)
    opp.life = 20
    me._match_opp = opp
    return me, opp


# ---- Searing Blaze (#119) -------------------------------------------------

def test_searing_blaze_no_landfall_is_1_1():
    me, opp = _caster_with_opp()
    opp.zones.battlefield.append(_creature("Grizzly Bears", 2, toughness=2))
    me._land_entered_this_turn = False          # no land this turn
    _searing_blaze_spell(me, Card(name="Searing Blaze", mana_cost="{R}{R}", cmc=2.0, type_line="Instant"))
    assert len(opp.zones.battlefield) == 1, "1 damage must not kill a 2-toughness creature"
    assert opp.life == 19, f"face damage should be 1 without landfall, got {20 - opp.life}"


def test_searing_blaze_landfall_is_3_3():
    me, opp = _caster_with_opp()
    opp.zones.battlefield.append(_creature("Grizzly Bears", 2, toughness=2))
    me._land_entered_this_turn = True           # a land entered this turn
    _searing_blaze_spell(me, Card(name="Searing Blaze", mana_cost="{R}{R}", cmc=2.0, type_line="Instant"))
    assert len(opp.zones.battlefield) == 0, "3 damage must kill a 2-toughness creature on landfall"
    assert opp.life == 17, f"face damage should be 3 with landfall, got {20 - opp.life}"


def test_searing_blaze_landfall_spares_toughness_4():
    me, opp = _caster_with_opp()
    opp.zones.battlefield.append(_creature("Tarmogoyf", 2, toughness=4))
    me._land_entered_this_turn = True
    _searing_blaze_spell(me, Card(name="Searing Blaze", mana_cost="{R}{R}", cmc=2.0, type_line="Instant"))
    assert len(opp.zones.battlefield) == 1, "even on landfall, 3 damage must not kill a 4-toughness creature"


def test_on_landfall_sets_the_flag():
    me = GameState(mainboard=[], on_play=True)
    assert getattr(me, "_land_entered_this_turn", False) is False
    on_landfall(me)
    assert me._land_entered_this_turn is True, "on_landfall must set the landfall gate"


# ---- Fatal Push (#118, conservative) --------------------------------------

def test_fatal_push_kills_cmc_2():
    me, opp = _caster_with_opp()
    opp.zones.battlefield.append(_creature("Ragavan", 1, toughness=2, power=2))
    _fatal_push_spell(me, Card(name="Fatal Push", mana_cost="{B}", cmc=1.0, type_line="Instant"))
    assert len(opp.zones.battlefield) == 0, "Fatal Push must kill a CMC-1 creature"


def test_fatal_push_spares_cmc_3_without_revolt():
    me, opp = _caster_with_opp()
    opp.zones.battlefield.append(_creature("Sc Apocalypse", 3, toughness=4, power=4))
    _fatal_push_spell(me, Card(name="Fatal Push", mana_cost="{B}", cmc=1.0, type_line="Instant"))
    assert len(opp.zones.battlefield) == 1, "without Revolt tracking, Fatal Push must NOT kill a CMC-3 creature"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("test_event_conditional_removal: OK")
