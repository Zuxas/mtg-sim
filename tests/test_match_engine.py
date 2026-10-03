"""
test_match_engine.py -- Smoke test for Phase 3A match engine

Loads two decks, wraps their APLs in GoldfishAdapter, runs matches.

Exit status: 0 only if EVERY phase succeeds (deck load, single match, 100-game set,
1000-game set); 1 otherwise. The success banner prints only after all phases pass.
Wrapped in main() so importing this module (e.g. pytest collection) runs nothing.
"""
import sys, os, time, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.deck import load_deck_from_file as load_deck
from apl.match_apl import GoldfishAdapter, GenericMatchAPL
from engine.match_engine import run_match, run_match_set, print_match_report

SUCCESS_BANNER = "Phase 3A smoke test complete!"


def _phase_failed(e):
    print(f"  ERROR: {e}")
    traceback.print_exc()
    print("\nPhase 3A smoke test FAILED")
    return 1


def _match_set(apl_a, deck_a, apl_b, deck_b, n, seed):
    print(f"\n--- {n}-game match set ---")
    t0 = time.time()
    results = run_match_set(apl_a, deck_a, apl_b, deck_b, n=n, seed=seed)
    elapsed = time.time() - t0
    print_match_report(results, "Boros Energy", "Izzet Prowess")
    print(f"  Time: {elapsed:.3f}s ({n/elapsed:.0f} games/sec)")


def main():
    # Load two decks
    print("Loading decks...")
    try:
        deck_a_cards, _ = load_deck("decks/boros_energy_modern.txt")
        deck_b_cards, _ = load_deck("decks/izzet_prowess_modern.txt")
        print(f"  Boros Energy: {len(deck_a_cards)} cards")
        print(f"  Izzet Prowess: {len(deck_b_cards)} cards")
    except Exception as e:
        print(f"  Deck load error: {e}")
        print("Cannot load decks, exiting")
        return 1

    # Use GenericMatchAPL for both (simplest test)
    apl_a = GenericMatchAPL()
    apl_a.name = "Boros Energy"
    apl_b = GenericMatchAPL()
    apl_b.name = "Izzet Prowess"

    # Single match test
    print("\n--- Single match test ---")
    try:
        t0 = time.time()
        result = run_match(apl_a, deck_a_cards, apl_b, deck_b_cards, seed=42)
        elapsed = time.time() - t0
        print(f"  Winner: Player {result.winner} on turn {result.kill_turn}")
        print(f"  Life: A={result.final_life_a} B={result.final_life_b}")
        print(f"  Damage: A dealt {result.damage_by_a}, B dealt {result.damage_by_b}")
        print(f"  Method: {result.win_method}")
        print(f"  Time: {elapsed:.3f}s")
    except Exception as e:
        return _phase_failed(e)

    # N-game match sets -- a failure in ANY of them, including the largest, fails the run
    for n, seed in ((100, 42), (1000, 123)):
        try:
            _match_set(apl_a, deck_a_cards, apl_b, deck_b_cards, n, seed)
        except Exception as e:
            return _phase_failed(e)

    print(f"\n{SUCCESS_BANNER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
