"""test_protection_keywords.py — synthetic tests for Phase 3.5 Stage C.

Covers can_be_targeted_by + ward_cost for HEXPROOF / SHROUD / WARD /
PROTECTION cluster. Validates the chokepoint helper behavior in
isolation from the simulator.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from engine.keywords import can_be_targeted_by, ward_cost, KWTag


def _mk(name, oracle="", colors=None, type_line="Creature", tags=None):
    c = Card(name=name, mana_cost="{1}", cmc=1, type_line=type_line,
             oracle_text=oracle, power="2", toughness="2",
             colors=colors or [])
    if tags:
        c.tags.update(tags)
    return c


def test_hexproof_asymmetric():
    """Opponent can't target hexproof creature; controller can."""
    bogle = _mk("Slippery Bogle", tags={KWTag.HEXPROOF})
    assert can_be_targeted_by(bogle, source=None, controller_is_opp=True) is False, \
        "opp targeting hexproof should fail"
    assert can_be_targeted_by(bogle, source=None, controller_is_opp=False) is True, \
        "controller targeting their own hexproof creature should succeed"


def test_shroud_blocks_all():
    """Shroud blocks targeting from anyone, including controller."""
    troll = _mk("Troll Ascetic", tags={KWTag.SHROUD})
    assert can_be_targeted_by(troll, source=None, controller_is_opp=True) is False
    assert can_be_targeted_by(troll, source=None, controller_is_opp=False) is False, \
        "shroud blocks even controller"


def test_ward_cost_reported_asymmetrically():
    """Ward cost applies only to opp-targeting; controller pays nothing."""
    sheo = _mk("Sheoldred", oracle="Ward {2}\nWhen ~ enters, you draw and lose 2.",
               tags={KWTag.WARD})
    assert ward_cost(sheo, controller_is_opp=True) == 2
    assert ward_cost(sheo, controller_is_opp=False) == 0, \
        "controller pays no ward when targeting own creature"

    no_ward = _mk("Plain Creature")
    assert ward_cost(no_ward, controller_is_opp=True) == 0


def test_protection_from_color_blocks_matching_source():
    """Protection from red blocks red source, allows non-red."""
    paladin = _mk("White Knight", oracle="Protection from red and from black",
                  colors=["W"], tags={KWTag.PROTECTION})
    red_bolt = _mk("Lightning Bolt", colors=["R"], type_line="Instant")
    blue_counter = _mk("Counterspell", colors=["U"], type_line="Instant")

    assert can_be_targeted_by(paladin, source=red_bolt, controller_is_opp=True) is False, \
        "red source blocked by protection from red"
    assert can_be_targeted_by(paladin, source=blue_counter, controller_is_opp=True) is True, \
        "blue source not blocked by protection from red/black"


def test_hexproof_plus_ward_hexproof_preempts():
    """Hexproof + Ward N — hexproof preempts (ward never asked)."""
    fortified = _mk("Fortified Beastie",
                    oracle="Hexproof\nWard {3}",
                    tags={KWTag.HEXPROOF, KWTag.WARD})
    # Targeting fails at hexproof; ward cost would be 3 but is never queried by APL
    assert can_be_targeted_by(fortified, source=None, controller_is_opp=True) is False
    # Ward cost still parseable for controller path (no-op since hexproof asymmetric)
    assert ward_cost(fortified, controller_is_opp=True) == 3, \
        "ward parser independent of hexproof check"


if __name__ == "__main__":
    test_hexproof_asymmetric()
    test_shroud_blocks_all()
    test_ward_cost_reported_asymmetrically()
    test_protection_from_color_blocks_matching_source()
    test_hexproof_plus_ward_hexproof_preempts()
    print("ALL 5 TESTS PASS")
