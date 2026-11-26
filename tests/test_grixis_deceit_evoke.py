"""
test_grixis_deceit_evoke.py -- Grixis Elementals uses Deceit the way the
card works.

Deceit: {4}{U/B}{U/B} creature, evoke {U/B}{U/B}; when it enters, if {U}{U}
was spent, return a nonland permanent to its owner's hand. The APL listed it
as a "{2UB} bounce" in a removal table whose generic path charged the printed
six mana, put Deceit in the graveyard, and could fire on the opponent's turn.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apl.grixis_elementals_standard_match import DECEIT, GrixisElementalsStandardMatchAPL
from data.card import Card, Tag
from engine.card_db import CardDB
from engine.mana import ManaPool


def state(pool_u=0, pool_b=0):
    d = CardDB().get(DECEIT)
    deceit = Card(name=DECEIT, mana_cost=d["mana_cost"], cmc=d["cmc"], type_line=d["type_line"])
    target = Card(name="Bear", mana_cost="{1}{G}", cmc=2, type_line="Creature",
                  power="2", toughness="2")
    target.tags = {Tag.CREATURE}
    pool = ManaPool()
    pool.U, pool.B = pool_u, pool_b
    z = lambda **k: type("Z", (), k)()
    gs = type("GS", (), {"zones": z(hand=[deceit], graveyard=[], battlefield=[]),
                         "mana_pool": pool, "spells_cast_this_turn": 0,
                         "noncreature_spells_this_turn": 0,
                         "_log": lambda self, m: None})()
    opp = type("GS", (), {"zones": z(battlefield=[target], hand=[], graveyard=[], exile=[])})()
    return gs, opp, deceit, target


def main():
    d = CardDB().get(DECEIT)
    assert d["mana_cost"] == "{4}{U/B}{U/B}" and "Evoke {U/B}{U/B}" in d["oracle_text"]
    assert "Flash" not in d["oracle_text"] and "Creature" in d["type_line"]
    assert "if {U}{U} was spent to cast it, return up to one other target nonland permanent" \
        in d["oracle_text"]
    apl = GrixisElementalsStandardMatchAPL()

    gs, opp, deceit, target = state(pool_u=2)
    assert apl._evoke_deceit(gs, opp, target)
    assert gs.mana_pool.total() == 0 and gs.zones.graveyard == [deceit]
    assert opp.zones.hand == [target] and not opp.zones.battlefield
    print("PASS: evoked for {U}{U}: target returned to hand, Deceit sacrificed")

    gs, opp, deceit, target = state(pool_u=1, pool_b=1)
    assert not apl._evoke_deceit(gs, opp, target)
    assert gs.zones.hand == [deceit] and opp.zones.battlefield == [target]
    print("PASS: no bounce without two blue mana")

    # On the opponent's turn the engine calls pre_combat_instant: Deceit has
    # no flash and must stay in hand.
    gs, opp, deceit, target = state(pool_u=6, pool_b=6)
    target.name = "Mightform Harmonizer"            # a kill-priority name
    apl.pre_combat_instant(gs, opp)
    assert gs.zones.hand == [deceit] and opp.zones.battlefield == [target]
    assert DECEIT not in apl.MATCH_REMOVAL
    print("PASS: Deceit is not cast in the opponent's turn window")


def sultai_control():
    """Sultai Control had the same table entry; it now evokes Deceit in its
    own main phase and leaves it alone on the opponent's turn."""
    from apl.sultai_control_standard_match import (
        KILL_PRIORITY, SultaiControlStandardMatchAPL)
    apl = SultaiControlStandardMatchAPL()
    assert DECEIT not in apl.MATCH_REMOVAL

    gs, opp, deceit, target = state(pool_u=6, pool_b=6)
    target.name = KILL_PRIORITY[0]
    apl.pre_combat_instant(gs, opp)
    assert gs.zones.hand == [deceit] and opp.zones.battlefield == [target]

    apl._match_cast_removal(gs, opp)
    assert gs.zones.graveyard == [deceit] and opp.zones.hand == [target]
    assert gs.mana_pool.total() == 10                 # two mana, not six
    print("PASS: Sultai Control evokes Deceit for two mana in its own main "
          "phase only")


if __name__ == "__main__":
    sultai_control()
    main()
