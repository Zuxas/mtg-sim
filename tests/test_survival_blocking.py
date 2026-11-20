"""
test_survival_blocking.py -- the opt-in survival-first blocker, and
Mono-Green Landfall using it instead of never blocking.

survival_blocking(blockers, attackers, life):
  - no blocks while the unblocked attack is not lethal (the deck is racing)
  - when it is lethal, the cheapest legal chump blocks that keep the
    defender alive
  - {} when no legal blocks prevent lethal
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from engine.match_state import combat_damage, survival_blocking


def creature(name, p, t, *kw):
    c = Card(name=name, mana_cost="{1}", cmc=1, type_line="Creature",
             power=str(p), toughness=str(t))
    c.tags = {Tag.CREATURE, *kw}
    return c


def face(attackers, blocks, life):
    """Damage the defending player actually takes with these blocks."""
    return combat_damage(attackers, blocks, defender_life=life).face


def main():
    bear, elf, wall = creature("Bear", 2, 2), creature("Elf", 1, 1), creature("Wall", 0, 4)

    # 1. Racing: 5 power into 20 life is not lethal, so no block.
    a = [creature("Ogre", 5, 5)]
    assert survival_blocking([bear, elf], a, 20) == {}
    print("PASS: no block while the attack is not lethal")

    # 2. Simplest lethal chump: one 5/5 into 5 life, the cheapest creature blocks.
    blocks = survival_blocking([bear, elf], a, 5)
    assert blocks == {id(a[0]): [elf]}, blocks
    assert face(a, blocks, 5) == 0
    print("PASS: one lethal attacker is chump-blocked by the cheapest creature")

    # 3. Several attackers: block only as many as needed, biggest first.
    a = [creature("Ogre", 5, 5), creature("Wolf", 3, 3), creature("Rat", 1, 1)]
    blocks = survival_blocking([bear, elf], a, 6)       # 9 incoming, 6 life
    assert list(blocks) == [id(a[0])], blocks            # stopping the 5 is enough
    assert face(a, blocks, 6) == 4
    print("PASS: blocks only what is needed to survive")

    # 4. Flying: a ground creature cannot block it; a reach creature can.
    a = [creature("Drake", 4, 4, "flying")]
    assert survival_blocking([bear, elf], a, 4) == {}
    spider = creature("Spider", 1, 3, "reach")
    assert survival_blocking([bear, spider], a, 4) == {id(a[0]): [spider]}
    print("PASS: flying needs a flying or reach blocker")

    # 5. Menace needs two blockers.
    a = [creature("Brute", 6, 6, "menace")]
    assert survival_blocking([bear], a, 6) == {}
    blocks = survival_blocking([bear, elf], a, 6)
    assert sorted(b.name for b in blocks[id(a[0])]) == ["Bear", "Elf"]
    print("PASS: menace is blocked by two creatures or not at all")

    # 6. Trample: only the blocker's toughness is soaked.
    a = [creature("Wurm", 6, 6, "trample")]
    assert survival_blocking([elf], a, 5) == {}          # 5 still tramples over
    blocks = survival_blocking([elf, wall], a, 5)        # Wall soaks 4, 2 through
    assert blocks == {id(a[0]): [wall]}, blocks
    assert face(a, blocks, 5) == 2
    print("PASS: a trampler is blocked by toughness, and only if that saves us")

    # 7. Double strike counts twice.
    a = [creature("Duelist", 3, 3, "double_strike")]
    assert survival_blocking([elf], a, 6) == {id(a[0]): [elf]}
    print("PASS: double strike is counted as two hits")

    # 8. Mono-Green Landfall used to return {} always.
    from apl.mono_green_landfall_standard_match import MonoGreenLandfallStandardMatchAPL
    apl = MonoGreenLandfallStandardMatchAPL()
    a = [creature("Ogre", 5, 5)]
    tapped = creature("Tapped", 3, 3)
    tapped.tapped = True

    class GS:
        zones = type("Z", (), {"battlefield": [bear, elf, tapped]})()
        life = 5
    assert apl.declare_blockers(GS, None, a) == {id(a[0]): [elf]}
    GS.life = 20
    assert apl.declare_blockers(GS, None, a) == {}
    GS.life, GS.zones.battlefield = 5, [tapped]
    assert apl.declare_blockers(GS, None, a) == {}       # tapped creatures cannot block
    print("PASS: Mono-Green Landfall chump-blocks lethal, races otherwise")


if __name__ == "__main__":
    main()
