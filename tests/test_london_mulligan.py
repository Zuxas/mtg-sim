"""test_london_mulligan.py -- issue #14.

match_engine applied the mulligan penalty twice (drew 7-N, then bottomed N).
match_runner ignored the APL's keep()/bottom() and drew max(4, 6-N) cards.
All three paths (goldfish, match_engine, match_runner) now share
apl.mulligan.take_opening_hand: draw 7, bottom N on keep.
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from apl.match_apl import MatchAPL
from apl.mulligan import take_opening_hand
from engine.game_state import GameState
from engine import match_engine, match_runner


def _deck():
    lands = [Card(name="Mountain", mana_cost="", cmc=0, type_line="Basic Land - Mountain",
                  oracle_text="", colors=[]) for _ in range(24)]
    spells = [Card(name=f"Spell {i}", mana_cost="{R}", cmc=1, type_line="Instant",
                   oracle_text="", colors=["R"]) for i in range(36)]
    return lands + spells


class Mull(MatchAPL):
    """Mulligans exactly `n` times, records every hand size it is shown, and
    bottoms lands first."""
    name = "mull"

    def __init__(self, n, bottom_count=None):
        self.n, self.bottom_count = n, bottom_count
        self.sizes_seen = []
        self.bottom_calls = []

    def keep(self, hand, mulligans=0, on_play=True):
        self.sizes_seen.append(len(hand))
        return mulligans >= self.n

    def bottom(self, hand, n):
        self.bottom_calls.append(n)
        picks = sorted(hand, key=lambda c: not c.is_land())
        return picks[:n if self.bottom_count is None else self.bottom_count]

    def main_phase(self, gs): pass
    def main_phase_match(self, gs, opp): pass
    def declare_attackers(self, gs, opp): return []
    def declare_blockers(self, gs, opp, attackers): return {}
    def end_step_actions(self, gs, opp): pass


def test_match_engine_hand_sizes_7_6_5_4():
    for n in range(4):
        apl = Mull(n)
        gs = GameState(_deck(), on_play=True)
        gs.zones.library = list(gs.mainboard)
        rng = random.Random(n)
        rng.shuffle(gs.zones.library)
        took = match_engine._do_mulligan(apl, gs, rng)
        assert took == n and len(gs.zones.hand) == 7 - n, (n, took, len(gs.zones.hand))
        assert len(gs.zones.hand) + len(gs.zones.library) == 60
        assert all(s == 7 for s in apl.sizes_seen), apl.sizes_seen   # always shown 7


def test_match_runner_hand_sizes_and_apl_is_asked():
    for n in range(4):
        a, b = Mull(n), Mull(0)
        gs = match_runner.TwoPlayerGameState(_deck(), _deck(), on_play=True, seed=n)
        took_a = match_runner._opening_hand(gs, "a", a)
        took_b = match_runner._opening_hand(gs, "b", b)
        assert (took_a, len(gs.hand_a)) == (n, 7 - n), (n, took_a, len(gs.hand_a))
        assert (took_b, len(gs.hand_b)) == (0, 7)
        assert len(gs.hand_a) + len(gs.lib_a) == 60
        assert a.sizes_seen and all(s == 7 for s in a.sizes_seen), a.sizes_seen
        assert a.bottom_calls == ([n] if n else []), a.bottom_calls


def test_fourth_hand_is_kept_without_asking():
    apl = Mull(99)       # would mulligan forever
    gs = match_runner.TwoPlayerGameState(_deck(), _deck(), on_play=True, seed=1)
    assert match_runner._opening_hand(gs, "a", apl) == 3
    assert len(gs.hand_a) == 4 and len(apl.sizes_seen) == 3


def test_bottom_choice_is_respected_and_short_bottoms_are_trimmed():
    apl = Mull(2)
    gs = match_runner.TwoPlayerGameState(_deck(), _deck(), on_play=True, seed=3)
    match_runner._opening_hand(gs, "a", apl)
    assert all(c.is_land() for c in gs.lib_a[-2:]), "bottomed cards go to the bottom of the library"
    import apl.mulligan as mull, io, contextlib
    os.environ.pop("SIM_DEBUG", None)
    before = mull.BAD_BOTTOMS
    lazy = Mull(2, bottom_count=0)     # bottom() returns nothing
    gs = match_runner.TwoPlayerGameState(_deck(), _deck(), on_play=True, seed=3)
    with contextlib.redirect_stdout(io.StringIO()):
        match_runner._opening_hand(gs, "a", lazy)
    assert len(gs.hand_a) == 5, len(gs.hand_a)
    assert mull.BAD_BOTTOMS == before + 1, "a corrected bottom() is counted"
    os.environ["SIM_DEBUG"] = "1"      # strict mode: raise instead
    try:
        gs = match_runner.TwoPlayerGameState(_deck(), _deck(), on_play=True, seed=3)
        match_runner._opening_hand(gs, "a", Mull(2, bottom_count=0))
        raise AssertionError("SIM_DEBUG should raise on a bad bottom()")
    except ValueError:
        pass
    finally:
        del os.environ["SIM_DEBUG"]


def test_seeded_and_reproducible():
    def hand(seed):
        gs = match_runner.TwoPlayerGameState(_deck(), _deck(), on_play=True, seed=seed)
        match_runner._opening_hand(gs, "a", Mull(1))
        return [c.name for c in gs.hand_a]
    assert hand(7) == hand(7)


def test_goldfish_default_still_shuffles():
    random.seed(5)
    hand, library, m = take_opening_hand(_deck())
    assert len(hand) == 7 - m and len(hand) + len(library) == 60


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_london_mulligan: OK")
