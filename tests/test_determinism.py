"""test_determinism.py -- Stage 1.7 regression test.

Two consecutive run_match_set calls with the same seed must produce
bit-identical results, regardless of the global random module's
state at entry. Pre-Stage-1.7, naked random.foo() consumers in
engine code (zones.shuffle, opponent.py, race.py, several handler
sites) leaked through global random state changes between calls,
producing per-matchup variance up to ±2.5pp at n=1000.

Spec: harness/specs/2026-04-28-stage-1.7-event-bus-determinism.md
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.deck import load_deck_from_file
from engine.match_runner import run_match_set
from apl.boros_energy import BorosEnergyAPL


def _be_deck():
    main, _ = load_deck_from_file('decks/boros_energy_modern.txt')
    return main


def test_match_set_deterministic_across_consecutive_calls():
    """Two seed=42 mirror runs in same process must match bit-exactly."""
    deck = _be_deck()
    r1 = run_match_set(BorosEnergyAPL(), deck, BorosEnergyAPL(), deck,
                       n=20, seed=42, mix_play_draw=True)
    r2 = run_match_set(BorosEnergyAPL(), deck, BorosEnergyAPL(), deck,
                       n=20, seed=42, mix_play_draw=True)
    assert r1.a_wins == r2.a_wins, f"a_wins drift: {r1.a_wins} vs {r2.a_wins}"
    assert r1.b_wins == r2.b_wins, f"b_wins drift: {r1.b_wins} vs {r2.b_wins}"
    assert r1.avg_turns == r2.avg_turns, \
        f"avg_turns drift: {r1.avg_turns} vs {r2.avg_turns}"


def test_match_set_preserves_global_random_state():
    """run_match_set's save/seed/restore must leave global random unchanged."""
    deck = _be_deck()
    random.seed(12345)
    pre_state = random.getstate()
    run_match_set(BorosEnergyAPL(), deck, BorosEnergyAPL(), deck,
                  n=5, seed=42, mix_play_draw=True)
    post_state = random.getstate()
    assert pre_state == post_state, \
        "global random state mutated by run_match_set; save/restore broken"


def test_match_set_deterministic_under_polluted_global_random():
    """Even if caller's global random advances between calls, results match."""
    deck = _be_deck()
    random.seed(0)
    r1 = run_match_set(BorosEnergyAPL(), deck, BorosEnergyAPL(), deck,
                       n=10, seed=42, mix_play_draw=True)
    # Pollute global random heavily between calls
    for _ in range(1000):
        random.random()
    r2 = run_match_set(BorosEnergyAPL(), deck, BorosEnergyAPL(), deck,
                       n=10, seed=42, mix_play_draw=True)
    assert r1.a_wins == r2.a_wins and r1.avg_turns == r2.avg_turns, \
        "pollution of global random leaked through Stage 1.7 guard"


if __name__ == "__main__":
    test_match_set_deterministic_across_consecutive_calls()
    test_match_set_preserves_global_random_state()
    test_match_set_deterministic_under_polluted_global_random()
    print("ALL 3 TESTS PASS")
