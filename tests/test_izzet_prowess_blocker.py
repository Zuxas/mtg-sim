"""
test_izzet_prowess_blocker.py -- Izzet Prowess (Modern) uses the default
blocker, and the default blocker judges a prowess creature by its effective
power and toughness, not its printed stats.

IzzetProwessMatchAPL.declare_blockers returned {} always. It now inherits
MatchAPL.optimal_blocking (legal-only since #96), which reads
safe_power/safe_toughness -- both honor a creature's effective_power() /
effective_toughness() -- so a Monastery Swiftspear that is 2/3 after a
prowess trigger blocks as a 2/3, not a 1/2.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apl.izzet_prowess_match import IzzetProwessMatchAPL
from apl.match_apl import MatchAPL
from data.card import Card, Tag
from engine.match_state import optimal_blocking, safe_toughness


def creature(name, p, t, *kw):
    c = Card(name=name, mana_cost="{1}", cmc=1, type_line="Creature",
             power=str(p), toughness=str(t))
    c.tags = {Tag.CREATURE, *kw}
    return c


def main():
    assert IzzetProwessMatchAPL.declare_blockers is MatchAPL.declare_blockers
    print("PASS: Izzet Prowess inherits the default blocker")

    # A 1/2 Swiftspear blocking a 2/2: printed, it dies and the 2/2 lives, so
    # no block. After a prowess trigger it is 2/3: it kills the 2/2 and lives,
    # so the free block is taken. The blocker must be judged at effective P/T.
    swift = creature("Monastery Swiftspear", 1, 2)
    boost = {"p": 0, "t": 0}
    swift.effective_power = lambda: int(swift.power) + boost["p"]
    swift.effective_toughness = lambda: int(swift.toughness) + boost["t"]
    atk = creature("Attacker", 2, 2)

    assert safe_toughness(swift) == 2
    assert optimal_blocking([swift], [atk], 20, 99) == {}      # printed 1/2: no block
    boost["p"], boost["t"] = 1, 1                              # prowess: now 2/3
    assert safe_toughness(swift) == 3
    assert optimal_blocking([swift], [atk], 20, 99) == {id(atk): [swift]}
    print("PASS: the blocker is judged at its effective, boosted stats")

    # Chump lethal through the APL's own entry point.
    guide = creature("Goblin Guide", 2, 2)
    ogre = creature("Ogre", 5, 5)
    me = type("GS", (), {"life": 4, "zones": type("Z", (), {"battlefield": [guide]})()})
    opp = type("GS", (), {"zones": type("Z", (), {"battlefield": [ogre]})()})
    assert len(IzzetProwessMatchAPL().declare_blockers(me, opp, [ogre])[id(ogre)]) == 1
    me2 = type("GS", (), {"life": 20, "zones": type("Z", (), {"battlefield": [guide]})()})
    assert IzzetProwessMatchAPL().declare_blockers(me2, opp, [ogre]) == {}
    print("PASS: chumps lethal, races otherwise, through the APL")


if __name__ == "__main__":
    main()
