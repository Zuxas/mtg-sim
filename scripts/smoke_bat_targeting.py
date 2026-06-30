"""scripts/smoke_bat_targeting.py -- post-Bat-targeting-fix Dimir smoke.

Quick check that the new 4-tier Bat exile priority (narrow removal >
turn-skip > engine > fallback) doesn't crash and ideally moves WR vs
matchups where Bat picks matter most: Izzet Lessons (Monument), MGL
(Sapling Nursery / Earthbender Ascension), Esper Pixie (Pixie Guide /
Overlord), Izzet Prowess (Stormchaser's Talent).
"""
import sys, os, time
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MATCHUPS = [
    # (label, opp_apl_key, opp_deck_path)
    ("Izzet Lessons",        "izzetlessonstandard",   "decks/izzet_lessons_standard.txt"),
    ("Mono Green Landfall",  "monogreenlandfall",     "decks/mono_green_landfall_standard.txt"),
    ("Esper Pixie",          "esperpixie",            "decks/esper_pixie_standard.txt"),
    ("Izzet Prowess",        "izzetprowessstandard",  "decks/izzet_prowess_standard.txt"),
    ("Selesnya Landfall",    "selesnyalandfall",      "decks/selesnya_landfall_standard.txt"),
    ("Selesnya Ouroboroid",  "selesnyaouroboroid",    "decks/selesnya_ouroboroid_standard.txt"),
]

MY_KEY  = "dimirmidrangejermey"
MY_FILE = "decks/dimir_midrange_jermey_sleeved_standard.txt"
N_GAMES = 200


def _worker(args):
    label, opp_key, opp_file = args
    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match

    apl_a = get_match_apl(MY_KEY)
    apl_b = get_match_apl(opp_key)
    deck_a, _ = load_deck_from_file(MY_FILE)
    deck_b, _ = load_deck_from_file(opp_file)

    wins = errs = 0
    t0 = time.time()
    for s in range(N_GAMES):
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b,
                          seed=s, on_play=s % 2 == 0)
            if r.won:
                wins += 1
        except Exception:
            errs += 1
    return label, wins, errs, time.time() - t0


def main():
    t0 = time.time()
    print(f"Sleeved Dimir vs key matchups -- {N_GAMES}g each, post-Bat-fix")
    print("-" * 60)
    args = [(lbl, k, f) for (lbl, k, f) in MATCHUPS]
    with ProcessPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(_worker, a): a for a in args}
        results = []
        for fut in as_completed(futures):
            results.append(fut.result())
    results.sort(key=lambda r: -r[1])
    print(f"  {'Matchup':25s} {'Wins':>8s} {'WR':>8s} {'Errs':>6s}")
    print("  " + "-" * 50)
    for label, wins, errs, dt in results:
        print(f"  {label:25s} {wins:>3d}/{N_GAMES}  {100*wins/N_GAMES:>5.1f}%  {errs:>4d}    ({dt:.1f}s)")
    print(f"\nTotal: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
