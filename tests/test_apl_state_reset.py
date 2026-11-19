"""test_apl_state_reset.py -- issue #15.

APL objects are reused across games (G1-G3 of a Bo3, every match of a set).
Per-game counters kept on the APL leaked from game to game, so results
depended on how many games came before and on n_workers.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from apl.match_apl import MatchAPL
from engine.match_engine import run_match
from engine.bo3_match import run_bo3_set


def _lands(n=60):
    return [Card(name="Mountain", mana_cost="", cmc=0, type_line="Basic Land - Mountain",
                 oracle_text="", colors=[]) for _ in range(n)]


class Leaky(MatchAPL):
    """Keeps a counter on self, like IzzetAffinityMatchAPL._kappa_counters.
    Burns the opponent for the counter's value each turn, so any leak from an
    earlier game changes how fast (and whether) it wins."""
    name = "leaky"

    def __init__(self, bump=1):
        self.bump = bump          # config: must survive the reset
        self._counter = 0         # per-game state: must not
        self.seen_at_start = []

    def keep(self, hand, mulligans=0, on_play=True): return True
    def bottom(self, hand, n): return hand[:n]
    def main_phase(self, gs): pass

    def main_phase_match(self, gs, opp):
        if gs.turn == 1:
            self.seen_at_start.append(self._counter)
        self._counter += self.bump
        opp.life -= self._counter // 4

    def declare_attackers(self, gs, opp): return []
    def declare_blockers(self, gs, opp, attackers): return {}
    def end_step_actions(self, gs, opp): pass


def test_counter_starts_from_zero_every_game():
    a, b = Leaky(), Leaky()
    turns = [run_match(a, _lands(), b, _lands(), on_play=True, seed=s).kill_turn
             for s in range(4)]
    assert len(set(turns)) == 1, f"kill turn drifted across games: {turns}"


def test_config_set_before_first_game_survives():
    a, b = Leaky(bump=3), Leaky()
    for s in range(3):
        run_match(a, _lands(), b, _lands(), on_play=True, seed=s)
    assert a.bump == 3


def test_state_is_readable_after_a_game():
    a, b = Leaky(), Leaky()
    run_match(a, _lands(), b, _lands(), on_play=True, seed=1)
    assert a._counter > 0, "caller should still see the APL's end-of-game state"


def test_bo3_set_same_for_one_and_two_workers():
    def run(workers):
        r = run_bo3_set(Leaky(), _lands(), {}, Leaky(bump=2), _lands(), {},
                        n=12, seed=7, n_workers=workers)
        return (r.a_wins, r.b_wins, r.g1_wr_a, r.g2_wr_a, r.g3_rate, r.avg_total_turns)
    assert run(1) == run(2), (run(1), run(2))


def test_apl_with_uncopyable_attribute_still_runs():
    import threading, io, contextlib

    class Locked(Leaky):
        def __init__(self):
            super().__init__()
            self.lock = threading.Lock()      # deepcopy raises TypeError

    a, b = Locked(), Leaky()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        for s in range(3):
            run_match(a, _lands(), b, _lands(), on_play=True, seed=s)
    assert out.getvalue().count("[!APL RESET]") == 1, "warn once, not every game"
    assert out.getvalue().isascii()


def test_apl_can_own_its_reset():
    class Custom(Leaky):
        resets = 0

        def reset_game_state(self):
            self._counter = 0
            Custom.resets += 1

    a, b = Custom(), Leaky()
    a.tuned = 1
    run_match(a, _lands(), b, _lands(), on_play=True, seed=1)
    a.tuned = 2                               # changed between games: kept
    run_match(a, _lands(), b, _lands(), on_play=True, seed=2)
    assert Custom.resets == 2 and a.tuned == 2
    assert a.seen_at_start[-1] == 0


if __name__ == "__main__":
    test_apl_with_uncopyable_attribute_still_runs()
    test_apl_can_own_its_reset()
    test_counter_starts_from_zero_every_game()
    test_config_set_before_first_game_survives()
    test_state_is_readable_after_a_game()
    test_bo3_set_same_for_one_and_two_workers()
    print("test_apl_state_reset: OK")
