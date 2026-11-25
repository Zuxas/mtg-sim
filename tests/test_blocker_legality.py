"""
test_blocker_legality.py -- the default blocker (optimal_blocking) only makes
legal blocks. It shares can_block / legal_blockers / blockers_needed with
survival_blocking. No strategy change is intended: the plain cases at the end
pin the choices it made before.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from engine.match_state import (blockers_needed, can_block, combat_damage,
                                legal_blockers, optimal_blocking)


def creature(name, p, t, *kw, text=""):
    c = Card(name=name, mana_cost="{1}", cmc=1, type_line="Creature",
             power=str(p), toughness=str(t), oracle_text=text)
    c.tags = {Tag.CREATURE, *kw}
    return c


def main():
    big = creature("Big", 4, 4)

    # Legality helpers.
    tapped = creature("Tapped", 4, 4)
    tapped.tapped = True
    coward = creature("Coward", 4, 4, text="This creature can't block.")
    assert can_block(big) and not can_block(tapped) and not can_block(coward)
    drake = creature("Drake", 2, 2, "flying")
    spider = creature("Spider", 1, 3, "reach")
    assert legal_blockers(drake, [big, spider, tapped]) == [spider]
    assert legal_blockers(creature("Sneak", 2, 2, "unblockable"), [big]) == []
    assert blockers_needed(creature("Brute", 3, 3, "menace")) == 2
    print("PASS: can_block, legal_blockers and blockers_needed")

    bear = creature("Bear", 2, 2)

    # A tapped creature or one that can't block is never assigned, even when
    # the block would be free.
    assert optimal_blocking([tapped], [bear], 20, 99) == {}
    assert optimal_blocking([coward], [bear], 20, 99) == {}
    assert optimal_blocking([coward, big], [bear], 20, 99) == {id(bear): [big]}
    print("PASS: tapped and can't-block creatures are never assigned")

    # Unblockable and flying attackers.
    sneak = creature("Sneak", 2, 2, "unblockable")
    assert optimal_blocking([big], [sneak], 20, 99) == {}
    assert optimal_blocking([big], [sneak], 2, 99) == {}          # even when lethal
    assert optimal_blocking([big], [drake], 20, 99) == {}
    assert optimal_blocking([big, spider], [drake], 20, 99) == {id(drake): [spider]}
    print("PASS: unblockable is never blocked; flying needs flying or reach")

    # Menace: two blockers or none.
    brute = creature("Brute", 3, 3, "menace")
    assert optimal_blocking([big], [brute], 20, 99) == {}
    elf = creature("Elf", 1, 1)
    blocks = optimal_blocking([big, elf], [brute], 20, 99)
    assert sorted(b.name for b in blocks[id(brute)]) == ["Big", "Elf"], blocks
    print("PASS: menace is blocked by two creatures or not at all")

    # Trample: when chumping to survive, block where it stops the most damage.
    wurm = creature("Wurm", 6, 6, "trample")
    wall = creature("Wall", 0, 4)
    blocks = optimal_blocking([elf, wall], [wurm], 5, 99)
    assert blocks == {id(wurm): [wall]}, blocks
    assert combat_damage([wurm], blocks, defender_life=5).face == 2
    print("PASS: a lethal trampler is chumped by toughness")

    # Unchanged choices: free kill is taken, a pointless chump is not, a
    # lethal attack is chumped.
    ogre = creature("Ogre", 5, 5)
    assert optimal_blocking([big], [bear], 20, 99) == {id(bear): [big]}
    assert optimal_blocking([elf], [ogre], 20, 99) == {}
    assert optimal_blocking([elf], [ogre], 5, 99) == {id(ogre): [elf]}
    print("PASS: plain blocking choices are unchanged")


if __name__ == "__main__":
    main()
