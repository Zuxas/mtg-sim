"""test_noncombat_lethal.py -- issue #22.

match_engine.run_match only ended the game on combat damage. A player
burned to 0 in a main phase kept playing (including a full turn of their
own) and the kill was reported a turn late as 'monument_drain'.

Uses stub APLs and land-only decks so no card data is needed.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from apl.match_apl import MatchAPL
from engine.match_engine import run_match


def _lands(n=60):
    return [Card(name="Mountain", mana_cost="", cmc=0, type_line="Basic Land - Mountain",
                 oracle_text="", colors=[]) for _ in range(n)]


class _Stub(MatchAPL):
    """Does nothing except what `on_main` says; records each turn it takes."""

    def __init__(self, on_main=None):
        self.on_main = on_main
        self.turns = []

    def keep(self, hand, mulligans=0, on_play=True):
        return True

    def bottom(self, hand, n):
        return hand[:n]

    def main_phase(self, gs):
        pass

    def main_phase_match(self, gs, opp):
        self.turns.append(gs.turn)
        if self.on_main:
            self.on_main(gs, opp)

    def declare_attackers(self, gs, opp):
        return []

    def declare_blockers(self, gs, opp, attackers):
        return {}

    def end_step_actions(self, gs, opp):
        pass


def _burn_on(turn, self_dmg=0):
    def f(gs, opp):
        if gs.turn == turn:
            opp.life -= 20
            gs.life -= self_dmg
    return f


def test_burn_in_main_phase_ends_game_that_turn():
    a, b = _Stub(_burn_on(3)), _Stub()
    r = run_match(a, _lands(), b, _lands(), on_play=True, seed=3)
    assert r.winner == 'a', r.winner
    assert r.kill_turn == 3, r.kill_turn
    assert r.win_method == 'noncombat', r.win_method
    assert r.final_life_b == 0, r.final_life_b
    assert b.turns == [1, 2], f"dead player took another turn: {b.turns}"


def test_active_player_dying_on_own_turn_loses():
    a, b = _Stub(lambda gs, opp: setattr(gs, 'life', 0) if gs.turn == 2 else None), _Stub()
    r = run_match(a, _lands(), b, _lands(), on_play=True, seed=3)
    assert r.winner == 'b' and r.kill_turn == 2, (r.winner, r.kill_turn)
    assert b.turns == [1], b.turns


def test_both_at_zero_is_a_draw():
    a, b = _Stub(_burn_on(2, self_dmg=20)), _Stub()
    r = run_match(a, _lands(), b, _lands(), on_play=True, seed=3)
    assert r.winner == 'draw', r.winner


if __name__ == "__main__":
    test_burn_in_main_phase_ends_game_that_turn()
    test_active_player_dying_on_own_turn_loses()
    test_both_at_zero_is_a_draw()
    print("test_noncombat_lethal: OK")
