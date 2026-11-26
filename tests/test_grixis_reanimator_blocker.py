"""
test_grixis_reanimator_blocker.py -- Grixis Reanimator uses the default
blocker, which keeps a reanimated payoff unless the deck would die.

GrixisReanimatorMatchAPL.declare_blockers returned {} always. It now inherits
MatchAPL.optimal_blocking (legal-only since #96): it blocks only when the
block kills the attacker and the blocker survives, trades up, or must chump a
lethal attack. So Abhorrent Oculus / Archon of Cruelty are preserved to win
with on a non-lethal attack and spent only to avoid dying.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apl.grixis_reanimator_match import GrixisReanimatorMatchAPL
from apl.match_apl import MatchAPL
from data.card import Card, Tag


def creature(name, p, t, *kw):
    c = Card(name=name, mana_cost="{1}", cmc=1, type_line="Creature",
             power=str(p), toughness=str(t))
    c.tags = {Tag.CREATURE, *kw}
    return c


def state(life, mine, theirs):
    me = type("GS", (), {"life": life,
                         "zones": type("Z", (), {"battlefield": mine})()})
    opp = type("GS", (), {"zones": type("Z", (), {"battlefield": theirs})()})
    return me, opp


def main():
    assert GrixisReanimatorMatchAPL.declare_blockers is MatchAPL.declare_blockers
    print("PASS: Grixis Reanimator inherits the default blocker")

    apl = GrixisReanimatorMatchAPL()
    oculus = creature("Abhorrent Oculus", 5, 5)   # the payoff

    # A non-lethal 3/3: the 5/5 would kill it and survive, so the free block
    # is fine (the Oculus is still there next turn). A pointless chump is not
    # made, but this block costs nothing.
    atk3 = creature("Threat", 3, 3)
    me, opp = state(20, [oculus], [atk3])
    assert apl.declare_blockers(me, opp, [atk3]) == {id(atk3): [oculus]}

    # A non-lethal attack the Oculus cannot profitably block: do not chump it.
    big = creature("Giant", 8, 8)
    me, opp = state(20, [oculus], [big])
    assert apl.declare_blockers(me, opp, [big]) == {}
    print("PASS: the payoff is not thrown under a non-lethal attack")

    # Lethal: chump to live.
    me, opp = state(5, [oculus], [big])
    assert apl.declare_blockers(me, opp, [big]) == {id(big): [oculus]}
    print("PASS: chumps with the payoff only to avoid lethal")


if __name__ == "__main__":
    main()
