"""test_combo_play_draw.py -- issue #31.

In the ComboKillSampler path, A always took its turn N (attack + lethal check)
before the combo deck's turn-N kill was checked, even when A was on the draw
and the combo player's turn N came first. Half of all sampled games gave A a
free extra turn.

Fixed clock: ten untapped 2/2s appear on A's side at the start of a chosen
turn, so A deals exactly 20 that turn. The combo kill turn is pinned.
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from engine import match_runner
from engine.match_runner import ComboKillSampler, _run_match_with_combo


def _bear():
    c = Card(name="Grizzly Bears", mana_cost="{1}{G}", cmc=2, type_line="Creature - Bear",
             oracle_text="", power="2", toughness="2", colors=["G"])
    c.tags = set(getattr(c, "tags", None) or set()) | {Tag.CREATURE}
    c.summoning_sickness = False
    return c


def _lands():
    return [Card(name="Forest", mana_cost="", cmc=0, type_line="Basic Land - Forest",
                 oracle_text="", colors=[]) for _ in range(60)]


def _play(on_play, combo_kill_turn, a_ready_turn):
    """A's lethal attack becomes available on `a_ready_turn` (the attackers
    appear at the start of that turn)."""
    rng = random.Random(1)
    combo = ComboKillSampler("Fixed", rng)
    combo._kill_t = combo_kill_turn
    real = match_runner._simple_play_turn

    def play_turn(gs, player, apl=None):
        if gs.turn == a_ready_turn and not gs.bf_a:
            gs.bf_a = [_bear() for _ in range(10)]
    match_runner._simple_play_turn = play_turn
    try:
        return _run_match_with_combo(None, _lands(), combo, on_play, 15, rng)
    finally:
        match_runner._simple_play_turn = real


def test_same_turn_race_goes_to_whoever_is_on_the_play():
    # A's clock and the combo kill are both turn 4
    on_play = _play(True, combo_kill_turn=4, a_ready_turn=4)
    on_draw = _play(False, combo_kill_turn=4, a_ready_turn=4)
    assert on_play.won is True and on_play.kill_turn == 4
    assert on_draw.won is False and on_draw.kill_turn == 4, \
        "on the draw the combo player's turn 4 comes first"


def test_a_one_turn_faster_wins_either_way():
    for on_play in (True, False):
        r = _play(on_play, combo_kill_turn=4, a_ready_turn=3)
        assert r.won is True and r.kill_turn == 3, (on_play, r.won, r.kill_turn)


def test_a_one_turn_slower_loses_either_way():
    for on_play in (True, False):
        r = _play(on_play, combo_kill_turn=4, a_ready_turn=5)
        assert r.won is False and r.kill_turn == 4, (on_play, r.won, r.kill_turn)


if __name__ == "__main__":
    test_same_turn_race_goes_to_whoever_is_on_the_play()
    test_a_one_turn_faster_wins_either_way()
    test_a_one_turn_slower_loses_either_way()
    print("test_combo_play_draw: OK")
