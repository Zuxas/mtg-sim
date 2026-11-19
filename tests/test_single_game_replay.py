"""A seeded run_match must replay the same game, in both engines.

Engine code reaches for the global `random` (zones.shuffle, card handlers).
match_runner.run_match_set seeded it per game, but a single run_match did not,
and match_engine never did, so the same seed gave different games and the
match_engine smoke test drifted run to run.

Run: python tests/test_single_game_replay.py
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.deck import load_deck_from_file
from apl.boros_energy_match import BorosEnergyMatchAPL
from engine import match_engine, match_runner

DECK, _ = load_deck_from_file("decks/boros_energy_modern.txt")


def _fingerprint(engine, seed, noise):
    random.seed(noise)          # whatever the caller did before must not matter
    r = engine.run_match(BorosEnergyMatchAPL(), DECK, BorosEnergyMatchAPL(), DECK, seed=seed)
    winner = getattr(r, "winner", None) or r.won
    return (winner, r.kill_turn, getattr(r, "final_life_a", None), getattr(r, "final_life_b", None))


def _check(engine):
    for seed in range(25):
        assert _fingerprint(engine, seed, 1) == _fingerprint(engine, seed, 2), (
            f"{engine.__name__}: seed {seed} did not replay")


def test_match_engine_replays():
    _check(match_engine)


def test_match_runner_replays():
    _check(match_runner)


def test_callers_global_random_is_left_alone():
    for engine in (match_engine, match_runner):
        random.seed(99)
        expected = random.Random(99).random()
        engine.run_match(BorosEnergyMatchAPL(), DECK, BorosEnergyMatchAPL(), DECK, seed=3)
        assert random.random() == expected, f"{engine.__name__} disturbed global random"


def test_global_random_is_restored_when_a_game_raises():
    class Boom(BorosEnergyMatchAPL):
        def main_phase_match(self, gs, opponent):
            raise RuntimeError("boom")

    os.environ["SIM_DEBUG"] = "1"      # make the engines re-raise APL errors
    try:
        for engine in (match_engine, match_runner):
            random.seed(5)
            expected = random.Random(5).random()
            try:
                engine.run_match(Boom(), DECK, Boom(), DECK, seed=3)
            except RuntimeError:
                pass
            assert random.random() == expected, f"{engine.__name__} left global random seeded"
    finally:
        del os.environ["SIM_DEBUG"]


def test_match_engine_set_is_reproducible():
    def run():
        r = match_engine.run_match_set(BorosEnergyMatchAPL(), DECK, BorosEnergyMatchAPL(), DECK,
                                       n=40, seed=42)
        return r.a_wins, r.kill_turns
    assert run() == run()


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_single_game_replay: OK")
