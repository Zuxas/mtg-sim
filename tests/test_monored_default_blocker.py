"""
test_monored_default_blocker.py -- Mono Red uses the default blocker instead
of refusing every block.

MonoRedMatchAPL.declare_blockers returned {} always, so on the core engine
the burn deck never blocked, even when its creature could kill an attacker
and survive or when a chump block was the difference between living and
dying. It now inherits MatchAPL.optimal_blocking (legal-only since #96),
which still races but takes a free favorable block and chumps lethal.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apl.match_apl import MatchAPL
from apl.mono_red_match import MonoRedMatchAPL
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
    assert MonoRedMatchAPL.declare_blockers is MatchAPL.declare_blockers
    print("PASS: Mono Red inherits the default blocker")

    apl = MonoRedMatchAPL()
    swift = creature("Monastery Swiftspear", 1, 2)   # survives blocking a 1/1
    goblin = creature("Goblin Guide", 2, 2)
    tapped = creature("Tapped", 2, 2)
    tapped.tapped = True

    # Free favorable block: a 1/2 blocks an attacking 1/1 and lives.
    atk = creature("Rat", 1, 1)
    me, opp = state(20, [swift], [atk])
    assert apl.declare_blockers(me, opp, [atk]) == {id(atk): [swift]}
    print("PASS: takes a free favorable block")

    # No pointless chump when not under threat.
    ogre = creature("Ogre", 5, 5)
    me, opp = state(20, [goblin], [ogre])
    assert apl.declare_blockers(me, opp, [ogre]) == {}
    print("PASS: does not chump when it is not dying")

    # Chumps to survive lethal, but not with a tapped creature.
    me, opp = state(4, [goblin], [ogre])
    assert len(apl.declare_blockers(me, opp, [ogre])[id(ogre)]) == 1
    me, opp = state(4, [tapped], [ogre])
    assert apl.declare_blockers(me, opp, [ogre]) == {}
    print("PASS: chumps lethal, never with a tapped creature")


if __name__ == "__main__":
    main()
