"""
tests/test_no_fake_flying_draw.py -- spec harness/specs/2026-09-29-remove-fake-flying-draw.md

Run: python tests/test_no_fake_flying_draw.py   (or via pytest)

F1: goldfish combat with a flying attacker draws no card. The engine used to
draw one for ANY flying attacker ("Guide of Souls flying damage trigger"), a
rule no printed card has.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from engine.game_state import GameState
from engine.keywords import tag_keywords


def _card(name, oracle, p="2", t="2", type_line="Creature"):
    c = Card(name=name, mana_cost="{1}", cmc=1, type_line=type_line,
             oracle_text=oracle, power=p, toughness=t)
    tag_keywords(c)
    return c


def test_f1_flying_attack_draws_nothing():
    lib = [_card(f"Filler {i}", "", type_line="Land") for i in range(10)]
    gs = GameState(mainboard=[], on_play=True)
    gs.zones.library = lib          # a real library, or a draw would be silently empty
    gs.turn = 3
    flier = _card("Slickshot Show-Off", "Flying, haste")
    flier.summoning_sickness = False
    gs.zones.battlefield.append(flier)
    hand0, lib0 = len(gs.zones.hand), len(gs.zones.library)
    assert lib0 == 10
    gs.run_combat()
    assert len(gs.zones.hand) == hand0, "a flying attacker drew a card"
    assert len(gs.zones.library) == lib0
    assert gs.damage_dealt >= 2          # the attack itself still happened
    print("[ok] F1 flying attacker deals damage and draws nothing")


def main() -> int:
    test_f1_flying_attack_draws_nothing()
    print("ALL F1 GATES PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
