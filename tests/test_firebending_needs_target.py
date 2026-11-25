"""
test_firebending_needs_target.py -- Izzet Lessons does not cast Firebending
Lesson ("deals 2 damage to target creature") when there is no creature to
target. It used to cast it at an empty board to put a Lesson in the graveyard.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apl.izzet_lesson_standard_match import FIREBEND_LES, IzzetLessonStandardMatchAPL
from data.card import Card, Tag
from engine.card_db import CardDB


class Pool:
    def can_cast(self, cost, cmc):
        return True

    def pay(self, cost, cmc):
        pass


def state(creatures):
    lesson = Card(name=FIREBEND_LES, mana_cost="{R}", cmc=1, type_line="Instant")
    zones = lambda **k: type("Z", (), k)()
    gs = type("GS", (), {
        "zones": zones(hand=[lesson], graveyard=[], battlefield=[]),
        "mana_pool": Pool(), "noncreature_spells_this_turn": 0,
        "tap_lands": lambda self: None, "_log": lambda self, m: None})()
    opp = type("GS", (), {"zones": zones(battlefield=list(creatures), graveyard=[])})()
    return gs, opp, lesson


def creature(p, t):
    c = Card(name="C", mana_cost="{1}", cmc=1, type_line="Creature",
             power=str(p), toughness=str(t))
    c.tags = {Tag.CREATURE}
    return c


def main():
    text = CardDB().get(FIREBEND_LES)["oracle_text"]
    assert "damage to target creature" in text, text
    apl = IzzetLessonStandardMatchAPL()

    gs, opp, lesson = state([])
    apl.end_step_actions(gs, opp)
    assert gs.zones.hand == [lesson] and not gs.zones.graveyard
    print("PASS: not cast at an empty board")

    small = creature(2, 2)
    gs, opp, lesson = state([small])
    apl.end_step_actions(gs, opp)
    assert gs.zones.graveyard == [lesson] and opp.zones.graveyard == [small]
    print("PASS: kills a creature with toughness 2")

    big = creature(5, 5)
    gs, opp, lesson = state([big])
    apl.end_step_actions(gs, opp)
    assert gs.zones.graveyard == [lesson] and opp.zones.battlefield == [big]
    print("PASS: may be cast at a creature it cannot kill")


if __name__ == "__main__":
    main()
