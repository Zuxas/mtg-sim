"""test_reactive_mana_legal.py -- issue #74 section 3A (#21).

The core engine (match_engine, #62) must give the non-active player only
*legal* reactive mana: a player who tapped out on their own turn has no mana
for a counterspell or trick in the opponent's windows. The old match_runner
handed the reactive player a full pool regardless of tapped-land state; the
core taps real untapped lands via _tap_for_response, so these pin that it does.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from engine.match_state import MatchGameState
from engine.match_engine import _tap_for_response, _try_reactive_interaction
from apl.match_apl import GenericMatchAPL


def _swamp(tapped=False):
    c = Card(name="Swamp", mana_cost="", cmc=0, type_line="Basic Land - Swamp",
             oracle_text="({T}: Add {B}.)", colors=[])
    c.tapped = tapped  # keep Card's auto-detected Land tag so it counts as a land
    return c


def _bear():
    c = Card(name="Grizzly Bears", mana_cost="{1}{G}", cmc=2,
             type_line="Creature - Bear", oracle_text="", power="2", toughness="2",
             colors=["G"])
    c.tags = {Tag.CREATURE}
    return c


def _instant_kill():
    c = Card(name="Instant Kill", mana_cost="{1}{B}", cmc=2, type_line="Instant",
             oracle_text="Destroy target creature.", colors=["B"])
    c.tags = {Tag.INSTANT}
    return c


def _fresh():
    mgs = MatchGameState([], [], seed=1)
    a, b = mgs.gs_a, mgs.gs_b
    a.turn = b.turn = 1
    b.mana_pool.empty()
    return mgs, a, b


def test_tapped_out_player_gains_no_reactive_mana():
    _, _a, b = _fresh()
    b.zones.battlefield = [_swamp(tapped=True), _swamp(tapped=True)]
    _tap_for_response(b)
    assert b.mana_pool.total() == 0, "a tapped-out player must get no reactive mana"


def test_untapped_lands_give_reactive_mana():
    _, _a, b = _fresh()
    b.zones.battlefield = [_swamp(tapped=False), _swamp(tapped=False)]
    _tap_for_response(b)
    assert b.mana_pool.total() == 2, "untapped lands must produce reactive mana"


def test_tapped_out_player_cannot_cast_the_instant():
    mgs, a, b = _fresh()
    spell = _instant_kill()
    b.zones.hand = [spell]
    b.zones.battlefield = [_swamp(tapped=True), _swamp(tapped=True)]
    a.zones.battlefield = [_bear()]
    _tap_for_response(b)
    _try_reactive_interaction(GenericMatchAPL(), b, a, mgs, 'b')
    assert spell in b.zones.hand, "tapped out -> the instant cannot be cast reactively"
    assert len(a.zones.battlefield) == 1, "the bear should survive"


def test_untapped_player_can_cast_the_instant():
    mgs, a, b = _fresh()
    spell = _instant_kill()
    b.zones.hand = [spell]
    b.zones.battlefield = [_swamp(tapped=False), _swamp(tapped=False)]
    a.zones.battlefield = [_bear()]
    _tap_for_response(b)
    _try_reactive_interaction(GenericMatchAPL(), b, a, mgs, 'b')
    assert spell not in b.zones.hand, "untapped -> the instant is cast reactively"


def main():
    for fn in (test_tapped_out_player_gains_no_reactive_mana,
               test_untapped_lands_give_reactive_mana,
               test_tapped_out_player_cannot_cast_the_instant,
               test_untapped_player_can_cast_the_instant):
        fn()
        print(f"PASS: {fn.__name__}")
    print("All reactive-mana-legality checks passed")


if __name__ == "__main__":
    main()
