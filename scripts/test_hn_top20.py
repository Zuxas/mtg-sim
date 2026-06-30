"""Test the top-20 ladder UW Flash build vs the 15-archetype Standard field.

Compares to Zevin HN v2 baseline (68.6% FW post-fixes).
List source: Untapped.gg screenshot, 29-7 (81%) Standard Bo3 Ladder 2026-05-08.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from concurrent.futures import ProcessPoolExecutor, as_completed
from apl import get_match_apl
from data.deck import load_deck_from_file
from engine.match_runner import run_match


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
DECKS = {
    "Top-20 HN": "decks/azorius_high_noon_top20_standard.txt",
    "Zevin v2":  "decks/azorius_high_noon_standard.txt",
}
APL_KEY = "azoriushighnoon"
GAMES = 500


def run_matchup(args):
    name, deck_path, opp_name, opp_key, opp_path = args
    apl_a = get_match_apl(APL_KEY)
    apl_b = get_match_apl(opp_key)
    deck_a, _ = load_deck_from_file(deck_path)
    deck_b, _ = load_deck_from_file(opp_path)
    wins = 0
    for s in range(GAMES):
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b,
                          seed=s, on_play=(s % 2 == 0))
            if r.won: wins += 1
        except Exception:
            pass
    return name, opp_name, wins


def main():
    jobs = []
    for name, dp in DECKS.items():
        for opp_name, opp_key, opp_path, _ in FIELD:
            jobs.append((name, dp, opp_name, opp_key, opp_path))

    print(f"\n{len(jobs)} jobs ({len(DECKS)} variants x {len(FIELD)} opps), N={GAMES}/each\n")
    results = {n: {} for n in DECKS}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(run_matchup, j) for j in jobs]
        for f in as_completed(futs):
            n, opp, w = f.result()
            results[n][opp] = w

    print(f"{'Matchup':<22}  {'Top-20':>8}  {'Zevin v2':>10}  {'Delta':>8}")
    print("-" * 60)
    for opp_name, _, _, _ in FIELD:
        t = results['Top-20 HN'][opp_name] / GAMES * 100
        z = results['Zevin v2'][opp_name] / GAMES * 100
        d = t - z
        sign = '+' if d >= 0 else ''
        print(f"{opp_name:<22}  {t:>7.1f}%  {z:>9.1f}%  {sign}{d:>6.1f}pp")

    total_share = sum(s for _, _, _, s in FIELD)
    fw_t = sum((results['Top-20 HN'][n]/GAMES) * s for n, _, _, s in FIELD) / total_share * 100
    fw_z = sum((results['Zevin v2'][n]/GAMES) * s for n, _, _, s in FIELD) / total_share * 100
    print()
    print(f"FW WR Top-20 HN:  {fw_t:.1f}%")
    print(f"FW WR Zevin v2:   {fw_z:.1f}%")
    print(f"Delta:            {fw_t-fw_z:+.1f}pp")
    print(f"\nTotal: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
