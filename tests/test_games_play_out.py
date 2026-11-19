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


def test_match_engine_games_finish():
    _check(match_engine)


def test_match_runner_games_finish():
    _check(match_runner)


def _lands(n):
    from data.card import Card, Tag
    out = []
    for _ in range(n):
        c = Card(name="Mountain", mana_cost="", cmc=0.0, type_line="Basic Land - Mountain")
        c.tags = {Tag.LAND}
        out.append(c)
    return out


def test_drawing_from_an_empty_library_loses():
    """Rule 104.3c. A's deck is 12 lands, B's is 60. Nobody deals damage, so
    the only way the game ends is A failing to draw."""
    from apl.match_apl import GenericMatchAPL
    for engine in (match_engine, match_runner):
        r = engine.run_match(GenericMatchAPL(), _lands(12), GenericMatchAPL(), _lands(60),
                             on_play=True, seed=1)
        a_won = (r.winner == "a") if hasattr(r, "winner") else r.won
        # 12 cards and a draw a turn: gone by turn 13 at the latest, however
        # many cards a mulligan put back. Without the rule it runs to the cap.
        assert not a_won and r.kill_turn <= 13, (engine.__name__, a_won, r.kill_turn)
        if hasattr(r, "win_method"):
            assert r.win_method == "decked"


def test_a_long_game_is_played_to_its_end():
    """Two 30-land decks do nothing, so the game lasts until someone cannot
    draw: past turn 15, before the cap. The old cap called it at 15."""
    from apl.match_apl import GenericMatchAPL
    for engine in (match_engine, match_runner):
        r = engine.run_match(GenericMatchAPL(), _lands(30), GenericMatchAPL(), _lands(30),
                             on_play=True, seed=1)
        assert 15 < r.kill_turn < 40, (engine.__name__, r.kill_turn)
        if hasattr(r, "win_method"):
            assert r.win_method == "decked"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_games_play_out: OK")
