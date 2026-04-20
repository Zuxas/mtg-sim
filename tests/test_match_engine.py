"""
test_match_engine.py — Smoke test for Phase 3A match engine

Loads two decks, wraps their APLs in GoldfishAdapter, runs matches.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from data.deck import load_deck_from_file as load_deck
from apl.match_apl import GoldfishAdapter, GenericMatchAPL
from engine.match_engine import run_match, run_match_set, print_match_report

# Load two decks
print("Loading decks...")
try:
    deck_a_main, deck_a_sb = load_deck("decks/boros_energy_modern.txt")
    deck_b_main, deck_b_sb = load_deck("decks/izzet_prowess_modern.txt")
    deck_a_cards = deck_a_main
    deck_b_cards = deck_b_main
    print(f"  Boros Energy: {len(deck_a_cards)} cards")
    print(f"  Izzet Prowess: {len(deck_b_cards)} cards")
except Exception as e:
    print(f"  Deck load error: {e}")
    print("  Falling back to GenericMatchAPL with raw card lists...")
    deck_a_cards = None

if deck_a_cards is None:
    print("Cannot load decks, exiting")
    sys.exit(1)

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
    import traceback
    print(f"  ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

# N-game match set test
print("\n--- 100-game match set ---")
try:
    t0 = time.time()
    results = run_match_set(apl_a, deck_a_cards, apl_b, deck_b_cards,
                            n=100, seed=42)
    elapsed = time.time() - t0
    print_match_report(results, "Boros Energy", "Izzet Prowess")
    print(f"  Time: {elapsed:.3f}s ({100/elapsed:.0f} games/sec)")
except Exception as e:
    import traceback
    print(f"  ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

# 1000-game test
print("\n--- 1000-game match set ---")
try:
    t0 = time.time()
    results = run_match_set(apl_a, deck_a_cards, apl_b, deck_b_cards,
                            n=1000, seed=123)
    elapsed = time.time() - t0
    print_match_report(results, "Boros Energy", "Izzet Prowess")
    print(f"  Time: {elapsed:.3f}s ({1000/elapsed:.0f} games/sec)")
except Exception as e:
    import traceback
    print(f"  ERROR: {e}")
    traceback.print_exc()

print("\nPhase 3A smoke test complete!")
