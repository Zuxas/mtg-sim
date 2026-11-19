"""test_lethal_from_life.py -- issue #28.

match_runner used `damage_to_x >= 20` as a loss check. damage_to_x is
cumulative and never drops on lifegain, so a defender who had gained
life was declared dead while still above 0. Loss must come from life only.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from engine.match_runner import TwoPlayerGameState, MatchResult, _run_player_turn


def _bear():
    c = Card(name="Grizzly Bears", mana_cost="{1}{G}", cmc=2, type_line="Creature",
             oracle_text="", power="2", toughness="2", colors=["G"])
    c.summoning_sickness = False
    return c


def _gs(life_b, damage_to_b):
    gs = TwoPlayerGameState([], [], on_play=True, seed=1)
    gs.turn = 5
    gs.bf_a = [_bear()]
    gs.life_b = life_b
    gs.damage_to_b = damage_to_b
    return gs


def test_lifegain_defender_survives_cumulative_20():
    gs = _gs(life_b=30, damage_to_b=18)
    res = MatchResult()
    ended = _run_player_turn(gs, "a", None, skip_draw=True, result=res, turn_num=5)
    assert gs.damage_to_b == 20, gs.damage_to_b
    assert gs.life_b == 28, gs.life_b
    assert not ended, "B is at 28 life; game must not end"


def test_life_zero_still_ends_game():
    gs = _gs(life_b=2, damage_to_b=18)
    res = MatchResult()
    ended = _run_player_turn(gs, "a", None, skip_draw=True, result=res, turn_num=5)
    assert ended and res.won and res.loser_life == 0


if __name__ == "__main__":
    test_lifegain_defender_survives_cumulative_20()
    test_life_zero_still_ends_game()
    print("test_lethal_from_life: OK")
