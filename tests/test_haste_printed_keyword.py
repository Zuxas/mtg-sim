"""
tests/test_haste_printed_keyword.py -- spec harness/specs/2026-09-29-haste-from-printed-keyword.md

Run: python tests/test_haste_printed_keyword.py   (or via pytest)

H1 TAGS: haste only when it is one of the card's own printed keywords. The old
regex matched any text that MENTIONS haste (Ragavan's Dash reminder, Bloodghast's
condition, cards that grant haste to something else).
H2 DASH: GameState.cast_spell_dash pays the real cost, counts as a spell, lets the
creature attack this turn, and returns it to hand at the end step -- goldfish and
match paths.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from engine.keywords import KWTag, tag_keywords, get_keywords

RAGAVAN = "Ragavan, Nimble Pilferer"


def _card(name, oracle, type_line="Creature", mana_cost="{R}", cmc=1, p="2", t="1"):
    c = Card(name=name, mana_cost=mana_cost, cmc=cmc, type_line=type_line,
             oracle_text=oracle, power=p, toughness=t)
    tag_keywords(c)
    return c


# oracle text verbatim (Scryfall), trimmed only after the haste-relevant lines
HAS = {
    "Goblin Guide": "Haste\nWhenever this creature attacks, defending player reveals the top card of their library.",
    "Monastery Swiftspear": "Haste\nProwess (Whenever you cast a noncreature spell, this creature gets +1/+1 until end of turn.)",
    "Slickshot Show-Off": "Flying, haste\nWhenever you cast a noncreature spell, this creature gets +2/+0 until end of turn.",
    "Strangleroot Geist": "Haste\nUndying (When this creature dies, if it had no +1/+1 counters on it, return it to the battlefield under its owner's control with a +1/+1 counter on it.)",
}
HAS_NOT = {
    RAGAVAN: ("Whenever Ragavan deals combat damage to a player, create a Treasure token and exile the "
              "top card of that player's library. Until end of turn, you may cast that card.\nDash {1}{R} "
              "(You may cast this spell for its dash cost. If you do, it gains haste, and it's returned from "
              "the battlefield to its owner's hand at the beginning of the next end step.)"),
    "Bloodghast": ("This creature can't block.\nThis creature has haste as long as an opponent has 10 or "
                   "less life.\nLandfall -- Whenever a land you control enters, you may return this card "
                   "from your graveyard to the battlefield."),
    "Badgermole Cub": ("When this creature enters, earthbend 1. (Target land you control becomes a 0/0 "
                       "creature with haste that's still a land. Put a +1/+1 counter on it. When it dies or "
                       "is exiled, return it to the battlefield tapped.)\nWhenever you tap a creature for "
                       "mana, add an additional {G}."),
    "Ardyn, the Usurper": "Demons you control have menace, lifelink, and haste.",
    "Xenagos, God of Revels": ("Indestructible\nAt the beginning of combat on your turn, another target "
                               "creature you control gains haste and gets +X/+X until end of turn."),
}


def test_h1_printed_haste_only():
    for name, text in HAS.items():
        c = _card(name, text)
        assert KWTag.HASTE in c.tags, name
        assert KWTag.HASTE in get_keywords(c), name
    for name, text in HAS_NOT.items():
        c = _card(name, text)
        assert KWTag.HASTE not in c.tags, name
        assert KWTag.HASTE not in get_keywords(c), name
    # other keywords on the same lines are untouched
    assert KWTag.FLYING in _card("Slickshot Show-Off", HAS["Slickshot Show-Off"]).tags
    assert KWTag.PROWESS in _card("Monastery Swiftspear", HAS["Monastery Swiftspear"]).tags
    print("[ok] H1 haste only from a printed keyword")


def _gs_with_lands(lands):
    from engine.game_state import GameState
    gs = GameState(mainboard=[], on_play=True)
    gs.turn = 3
    for name, tl in lands:
        land = Card(name=name, mana_cost="", cmc=0, type_line=tl, oracle_text="")
        gs.zones.battlefield.append(land)
        gs.mana_pool.add_land(tl, name)
    return gs


def _ragavan():
    return _card(RAGAVAN, HAS_NOT[RAGAVAN], type_line="Legendary Creature - Monkey Pirate")


def test_h2_dash_goldfish_path():
    gs = _gs_with_lands([("Mountain", "Basic Land - Mountain"), ("Plains", "Basic Land - Plains")])
    rag = _ragavan()
    gs.zones.hand.append(rag)
    before = gs.spells_cast_this_turn
    assert gs.cast_spell_dash(rag)
    assert rag in gs.zones.battlefield and rag not in gs.zones.hand
    assert rag.summoning_sickness is False            # can attack this turn
    assert KWTag.HASTE not in rag.tags                # no permanent haste tag
    assert gs.spells_cast_this_turn == before + 1     # dash is casting a spell
    assert gs.mana_pool.total() == 0                  # paid {1}{R}
    gs._tick_dash()
    assert rag in gs.zones.hand and rag not in gs.zones.battlefield
    print("[ok] H2 dash pays 2, attacks now, returns at end step (goldfish)")


def test_h2_dash_needs_two_mana_and_red():
    one = _gs_with_lands([("Mountain", "Basic Land - Mountain")])
    rag = _ragavan()
    one.zones.hand.append(rag)
    assert not one.cast_spell_dash(rag) and rag in one.zones.hand
    no_red = _gs_with_lands([("Plains", "Basic Land - Plains"), ("Plains", "Basic Land - Plains")])
    rag2 = _ragavan()
    no_red.zones.hand.append(rag2)
    assert not no_red.cast_spell_dash(rag2)
    # a non-dash card is refused
    g = _gs_with_lands([("Mountain", "Basic Land - Mountain"), ("Mountain", "Basic Land - Mountain")])
    guide = _card("Goblin Guide", HAS["Goblin Guide"])
    g.zones.hand.append(guide)
    assert not g.cast_spell_dash(guide)
    print("[ok] H2 dash refused without {1}{R} or for a non-dash card")


def test_h2_dash_returns_in_match_end_step():
    from engine import match_runner as mr
    gs = mr.TwoPlayerGameState([], [], on_play=True, seed=1)
    rag = _ragavan()
    rag._dashed = True
    gs.bf_a.append(rag)
    mr._run_end_step(gs, "a", "b", None)
    assert rag in gs.hand_a and rag not in gs.bf_a and not rag._dashed
    print("[ok] H2 dashed creature returns to hand in the match end step")


def main() -> int:
    test_h1_printed_haste_only()
    test_h2_dash_goldfish_path()
    test_h2_dash_needs_two_mana_and_red()
    test_h2_dash_returns_in_match_end_step()
    print("ALL HASTE/DASH GATES PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
