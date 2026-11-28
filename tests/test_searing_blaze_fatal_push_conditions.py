"""Searing Blaze (#119) and Fatal Push (#118) must respect their conditions.

Both handlers baked their conditional "big mode" in as always-on:
  - Searing Blaze dealt 3/3 and killed toughness <= 3 unconditionally, when
    Landfall (a land entered under your control this turn) gates the 3/3 mode;
    base is 1/1 killing toughness <= 1.
  - Fatal Push destroyed any creature with mana value <= 4, when Revolt (a
    permanent left the battlefield under your control this turn) gates the <= 4
    mode; base is <= 2.

Searing Blaze now reads the existing per-turn land-drop flag (gs.land_played).
Fatal Push uses the base <= 2 threshold (the engine has no revolt signal yet).

Run: python tests/test_searing_blaze_fatal_push_conditions.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from engine.game_state import GameState
from engine.card_handlers_verified import _searing_blaze_spell, _fatal_push_spell


def _creature(name, power, toughness, cmc):
    c = Card(name=name, mana_cost="{1}", cmc=float(cmc),
             type_line="Creature - Test", power=str(power), toughness=str(toughness))
    c.tags = {Tag.CREATURE}
    return c


def _match(opp_board):
    """A caster GameState wired to an opponent whose battlefield is opp_board."""
    caster = GameState(mainboard=[], on_play=True)
    opp = GameState(mainboard=[], on_play=False)
    opp.zones.battlefield = list(opp_board)
    opp.life = 20
    caster._match_opp = opp
    caster.damage_dealt = 0
    return caster, opp


def test_searing_blaze_without_landfall_is_1_1():
    caster, opp = _match([_creature("Bear", 2, 2, 2)])
    caster.land_played = False                      # no land this turn
    _searing_blaze_spell(caster, None)
    assert opp.life == 19, f"base mode deals 1 to face, got {20 - opp.life}"
    assert len(opp.zones.battlefield) == 1, "a 2-toughness creature survives 1 damage"
    assert caster.damage_dealt == 1


def test_searing_blaze_with_landfall_is_3_3():
    caster, opp = _match([_creature("Bear", 2, 2, 2)])
    caster.land_played = True                        # land dropped this turn
    _searing_blaze_spell(caster, None)
    assert opp.life == 17, f"landfall deals 3 to face, got {20 - opp.life}"
    assert len(opp.zones.battlefield) == 0, "a 2-toughness creature dies to 3 damage"
    assert caster.damage_dealt == 3


def test_searing_blaze_base_kills_only_toughness_1():
    caster, opp = _match([_creature("X 1/1", 1, 1, 1), _creature("Y 2/2", 2, 2, 2)])
    caster.land_played = False
    _searing_blaze_spell(caster, None)
    names = [c.name for c in opp.zones.battlefield]
    assert "X 1/1" not in names and "Y 2/2" in names, f"base mode kills only toughness<=1; board={names}"


def test_fatal_push_kills_mv2_not_mv3_or_mv4():
    caster, opp = _match([_creature("MV4", 4, 4, 4), _creature("MV3", 3, 3, 3), _creature("MV2", 2, 2, 2)])
    _fatal_push_spell(caster, None)
    names = [c.name for c in opp.zones.battlefield]
    assert "MV2" not in names, "base Fatal Push destroys a MV2 creature"
    assert "MV3" in names and "MV4" in names, f"no Revolt: MV3/MV4 must survive; board={names}"


def test_fatal_push_no_target_when_all_above_2():
    caster, opp = _match([_creature("MV3", 3, 3, 3), _creature("MV4", 4, 4, 4)])
    _fatal_push_spell(caster, None)
    assert len(opp.zones.battlefield) == 2, "nothing MV<=2 to destroy, board unchanged"


if __name__ == "__main__":
    test_searing_blaze_without_landfall_is_1_1()
    test_searing_blaze_with_landfall_is_3_3()
    test_searing_blaze_base_kills_only_toughness_1()
    test_fatal_push_kills_mv2_not_mv3_or_mv4()
    test_fatal_push_no_target_when_all_above_2()
    print("test_searing_blaze_fatal_push_conditions: OK")
