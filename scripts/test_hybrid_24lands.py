"""Test 4 24-land variants of the Hybrid (UB Bounce + Jermey).

Each variant cuts 1 Long Goodbye (the 1-of with the smallest impact
across SB plans) and adds 1 of a different land. Compares each variant's
FW WR against the 15-archetype Standard field to the 23-land base.

Variants:
  v1: +1 Restless Reef  (4 total -- attacking manland)
  v2: +1 Fountainport   (2 total -- treasure utility)
  v3: +1 Multiversal Passage (4 total -- any-color)
  v4: +1 Starting Town  (4 total -- T1 untapped color)
"""
import sys, os, time
from copy import deepcopy
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from concurrent.futures import ProcessPoolExecutor, as_completed
from apl import get_match_apl
from data.deck import load_deck_from_file
from engine.match_runner import run_match


# Standard 15-archetype field (matches rc_hn_v2_validate.py)
FIELD = [
    ("Selesnya Landfall",   "selesnyalandfall",  "decks/selesnya_landfall_standard.txt",      0.049),
    ("Mono Green Landfall", "monogreenlandfall", "decks/mono_green_landfall_standard.txt",    0.049),
    ("Bant Airbending",     "bantairbending",    "decks/bant_airbending_standard.txt",        0.039),
    ("Bant Rhythm",         "bantrhythm",        "decks/bant_rhythm_standard.txt",            0.049),
    ("Simic Rhythm",        "simicrhythm",       "decks/simic_rhythm_standard.txt",           0.029),
    ("Sultai Reanimator",   "sultaireanimator",  "decks/sultai_reanimator_standard.txt",      0.029),
    ("Selesnya Ouroboroid", "selesnyaouroboroid","decks/selesnya_ouroboroid_standard.txt",    0.020),
    ("Izzet Prowess",       "izzetprowessstandard","decks/izzet_prowess_standard.txt",        0.245),
    ("Izzet Lessons",       "izzetlesson",       "decks/izzet_lesson_standard.txt",           0.118),
    ("Izzet Spellementals", "izzetspellementals","decks/izzet_spellementals_standard.txt",    0.078),
    ("Jeskai Control",      "jeskaicontrol",     "decks/jeskai_control_standard.txt",         0.069),
    ("Gruul Aggro",         "gruulaggro",        "decks/gruul_aggro_standard.txt",            0.029),
    ("Jeskai Lute",         "jeskailute",        "decks/jeskai_lute_standard.txt",            0.030),
    ("Dimir Excruciator",   "dimirexcruciator",  "decks/dimir_excruciator_standard.txt",      0.080),
    ("Golgari Midrange",    "golgarimidrange",   "decks/golgari_midrange_standard.txt",       0.040),
]

DECK_FILE = "decks/dimir_bounce_jermey_hybrid_standard.txt"
APL_KEY = "dimirmidrangejermey"
GAMES = 500

VARIANTS = {
    "base 23L":     None,                       # no change
    "v1 +Reef":     ("Long Goodbye", "Restless Reef"),
    "v2 +Fount":    ("Long Goodbye", "Fountainport"),
    "v3 +Passage":  ("Long Goodbye", "Multiversal Passage"),
    "v4 +Town":     ("Long Goodbye", "Starting Town"),
}


def build_variant(base_main, swap):
    """Cut 1 of card_out, add 1 of card_in (copying an existing land)."""
    if swap is None:
        return [deepcopy(c) for c in base_main]
    card_out, card_in = swap
    deck = [deepcopy(c) for c in base_main]
    # Find a template land of the desired type already in the deck
    template = next((c for c in deck if c.name == card_in), None)
    if template is None:
        raise ValueError(f"No template for {card_in} in deck")
    # Remove 1 card_out
    for i, c in enumerate(deck):
        if c.name == card_out:
            deck.pop(i)
            break
    else:
        raise ValueError(f"Couldn't find {card_out} to cut")
    # Add 1 of card_in
    deck.append(deepcopy(template))
    return deck


def run_matchup(args):
    variant_name, deck_main_pickled, opp_name, opp_key, opp_path, share = args
    import pickle
    deck_main = pickle.loads(deck_main_pickled)
    apl_a = get_match_apl(APL_KEY)
    apl_b = get_match_apl(opp_key)
    deck_b, _ = load_deck_from_file(opp_path)
    wins = 0
    for s in range(GAMES):
        try:
            r = run_match(apl_a, deck_main, apl_b, deck_b,
                          seed=s, on_play=(s % 2 == 0))
            if r.won:
                wins += 1
        except Exception:
            pass
    return variant_name, opp_name, wins, share


def main():
    base_main, _ = load_deck_from_file(DECK_FILE)
    import pickle

    # Build all variant decks
    variant_decks = {}
    for name, swap in VARIANTS.items():
        try:
            deck = build_variant(base_main, swap)
            assert len(deck) == 60, f"{name}: {len(deck)} cards"
            variant_decks[name] = pickle.dumps(deck)
            land_count = sum(1 for c in deck if c.is_land())
            print(f"  {name:<14} = {land_count} lands ({len(deck)} total)")
        except Exception as e:
            print(f"  {name:<14} BUILD FAIL: {e}")

    # Submit all (variant x matchup) jobs to process pool
    jobs = []
    for v_name, deck_pickled in variant_decks.items():
        for opp_name, opp_key, opp_path, share in FIELD:
            jobs.append((v_name, deck_pickled, opp_name, opp_key, opp_path, share))

    print(f"\n{len(jobs)} matchup jobs ({len(variant_decks)} variants x {len(FIELD)} opps), N={GAMES} each\n")

    results = {v: {} for v in variant_decks}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run_matchup, j) for j in jobs]
        for f in as_completed(futures):
            v_name, opp_name, wins, share = f.result()
            results[v_name][opp_name] = (wins, share)

    # Print per-variant FW WR
    print(f"\n{'Variant':<14}  {'FW WR':>7}  Per-matchup WR")
    print("-" * 80)
    for v_name in VARIANTS:
        if v_name not in results:
            continue
        r = results[v_name]
        total_share = sum(s for _, s in r.values())
        fw = sum((w / GAMES) * s for w, s in r.values()) / total_share * 100
        print(f"{v_name:<14}  {fw:>6.1f}%")
    print()
    # Detailed per-matchup table
    headers = ["Matchup"] + list(VARIANTS.keys())
    print(f"{'Matchup':<22}  " + "  ".join(f"{h:>10}" for h in VARIANTS))
    print("-" * 90)
    for opp_name, _, _, _ in FIELD:
        row = [opp_name]
        for v in VARIANTS:
            if v in results and opp_name in results[v]:
                w = results[v][opp_name][0]
                row.append(f"{w/GAMES*100:>9.1f}%")
            else:
                row.append("    -")
        print(f"{row[0]:<22}  " + "  ".join(f"{x:>10}" for x in row[1:]))

    print(f"\nTotal: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
