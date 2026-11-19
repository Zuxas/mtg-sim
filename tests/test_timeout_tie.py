"""test_timeout_tie.py -- issue #29.

Games that timed out with both players dead even always went to player B,
so a stalled mirror read as a 0% win rate. Ties are now a seeded coin flip
and counted in the set results.

Stub APLs on land-only decks: nobody can ever deal damage.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from apl.match_apl import MatchAPL
from engine import match_engine, match_runner


def _lands(n=60):
    return [Card(name="Mountain", mana_cost="", cmc=0, type_line="Basic Land - Mountain",
                 oracle_text="", colors=[]) for _ in range(n)]


class Idle(MatchAPL):
    name = "idle"

    def keep(self, hand, mulligans=0, on_play=True):
        return True

    def bottom(self, hand, n):
        return hand[:n]

    def main_phase(self, gs):
        pass

    def main_phase_match(self, gs, opp):
        pass

    def declare_attackers(self, gs, opp):
        return []

    def declare_blockers(self, gs, opp, attackers):
        return {}

    def end_step_actions(self, gs, opp):
        pass


def _check(res, n, label):
    assert res.ties == n, f"{label}: expected {n} ties, got {res.ties}"
    assert res.a_wins + res.b_wins == n
    assert 35 <= res.win_pct_a() <= 65, f"{label}: stalled mirror should be ~50%, got {res.win_pct_a()}%"


def test_match_engine_stalled_mirror_is_even():
    res = match_engine.run_match_set(Idle(), _lands(), Idle(), _lands(), n=200, seed=42)
    _check(res, 200, "match_engine")
    again = match_engine.run_match_set(Idle(), _lands(), Idle(), _lands(), n=200, seed=42)
    assert again.a_wins == res.a_wins, "coin flip must be seeded"


def test_match_runner_stalled_mirror_is_even():
    res = match_runner.run_match_set(Idle(), _lands(), Idle(), _lands(), n=200, seed=42)
    _check(res, 200, "match_runner")
    again = match_runner.run_match_set(Idle(), _lands(), Idle(), _lands(), n=200, seed=42)
    assert again.a_wins == res.a_wins, "coin flip must be seeded"


def test_unequal_life_at_timeout_is_not_a_tie():
    class Pinger(Idle):
        def main_phase_match(self, gs, opp):
            if gs.turn == 1:
                opp.life -= 1
    r = match_engine.run_match(Pinger(), _lands(), Idle(), _lands(), seed=1)
    assert r.winner == 'a' and r.win_method == 'timeout', (r.winner, r.win_method)


if __name__ == "__main__":
    test_match_engine_stalled_mirror_is_even()
    test_match_runner_stalled_mirror_is_even()
    test_unequal_life_at_timeout_is_not_a_tie()
    print("test_timeout_tie: OK")
