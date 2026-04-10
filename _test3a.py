import sys, os, time, traceback
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

print("=== Phase 3A Minimal Test ===")
print("Loading decks...")
from data.deck import load_deck_from_file
deck_a, _ = load_deck_from_file('decks/boros_energy_modern.txt')
deck_b, _ = load_deck_from_file('decks/izzet_prowess_modern.txt')
print(f"A: {len(deck_a)} cards, B: {len(deck_b)} cards")

print("\nCreating MatchGameState...")
from engine.match_state import MatchGameState
mgs = MatchGameState(deck_a, deck_b, seed=42)
print(f"  Lib A: {len(mgs.gs_a.zones.library)}, Lib B: {len(mgs.gs_b.zones.library)}")

# Test a single turn manually
print("\nManual turn test...")
from apl.match_apl import GenericMatchAPL
apl = GenericMatchAPL()

# Draw opening hand for A
for _ in range(7):
    if mgs.gs_a.zones.library:
        mgs.gs_a.zones.hand.append(mgs.gs_a.zones.library.pop(0))
print(f"  Hand A: {[c.name for c in mgs.gs_a.zones.hand]}")

# Check lands in hand
lands = [c for c in mgs.gs_a.zones.hand if c.is_land()]
nonlands = [c for c in mgs.gs_a.zones.hand if not c.is_land()]
print(f"  Lands: {len(lands)}, Nonlands: {len(nonlands)}")

# Try playing a land
mgs.gs_a.turn = 1
mgs.gs_a.land_played = False
print(f"  land_played before: {mgs.gs_a.land_played}")

try:
    apl.main_phase(mgs.gs_a)
    print(f"  After main_phase:")
    print(f"    Battlefield: {[c.name for c in mgs.gs_a.zones.battlefield]}")
    print(f"    Hand: {[c.name for c in mgs.gs_a.zones.hand]}")
    print(f"    Mana: {mgs.gs_a.mana_pool.total()}")
except Exception as e:
    print(f"  ERROR in main_phase: {e}")
    traceback.print_exc()

# Now try running a full match
print("\n=== Full match test ===")
try:
    from engine.match_engine import run_match
    apl_a = GenericMatchAPL()
    apl_b = GenericMatchAPL()
    t0 = time.time()
    result = run_match(apl_a, deck_a, apl_b, deck_b, seed=99)
    elapsed = time.time() - t0
    print(f"  Winner: Player {result.winner}")
    print(f"  Turn: {result.kill_turn}")
    print(f"  Method: {result.win_method}")
    print(f"  Life: A={result.final_life_a} B={result.final_life_b}")
    print(f"  Damage: A={result.damage_by_a} B={result.damage_by_b}")
    print(f"  Time: {elapsed:.3f}s")
except Exception as e:
    print(f"  ERROR: {e}")
    traceback.print_exc()

print("\nDone.")
