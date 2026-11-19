"""Games are played to a real finish, not called on life totals at turn 15.

At the old cap of 15, 1-2% of games stopped unfinished and the higher life
total was named the winner. Played out, about a fifth of those games are won
by the other player. The cap is now a safety net (40) that normal games never
reach.

Run: python tests/test_games_play_out.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.deck import load_deck_from_file
from apl.boros_energy_match import BorosEnergyMatchAPL
from engine import match_engine, match_runner

DECK, _ = load_deck_from_file("decks/boros_energy_modern.txt")


def _game(engine, seed, **kw):
    return engine.run_match(BorosEnergyMatchAPL(), DECK, BorosEnergyMatchAPL(), DECK,
                            seed=seed, on_play=seed % 2 == 0, **kw)


def _check(engine):
    long_games = 0
    for seed in range(300):
        r = _game(engine, seed)
        assert r.kill_turn < 40, f"{engine.__name__}: seed {seed} never finished"
        assert not getattr(r, "win_method", "").startswith("timeout")
        if r.kill_turn > 15:
            long_games += 1
            # the old cap would have stopped this game before anyone had won
            assert _game(engine, seed, max_turns=15).kill_turn >= 15
    assert long_games, "expected at least one game longer than 15 turns in 300"


def test_match_engine_games_finish():
    _check(match_engine)


def test_match_runner_games_finish():
    _check(match_runner)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_games_play_out: OK")
