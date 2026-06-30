"""Test Nick Odenheimer's Tokyo Prowess build vs the 15-archetype Standard field.

Compares Nick Tokyo to the PT consensus list (izzetprowessstandard).
List source: Worldly Counsel primer, RC Tokyo update 2026-05-10.
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
    ("Izzet Prowess (PT)",  "izzetprowessstandard","decks/izzet_prowess_standard.txt",        0.245),
    ("Izzet Lessons",       "izzetlesson",       "decks/izzet_lesson_standard.txt",           0.118),
    ("Izzet Spellementals", "izzetspellementals","decks/izzet_spellementals_standard.txt",    0.078),
    ("Jeskai Control",      "jeskaicontrol",     "decks/jeskai_control_standard.txt",         0.069),
    ("Gruul Aggro",         "gruulaggro",        "decks/gruul_aggro_standard.txt",            0.029),
    ("Jeskai Lute",         "jeskailute",        "decks/jeskai_lute_standard.txt",            0.030),
    ("Dimir Excruciator",   "dimirexcruciator",  "decks/dimir_excruciator_standard.txt",      0.080),
    ("Golgari Midrange",    "golgarimidrange",   "decks/golgari_midrange_standard.txt",       0.040),
]
DECKS = {
    "Nick Tokyo": ("izzetprowessstandardtokyo", "decks/izzet_prowess_nick_tokyo_standard.txt"),
    "PT consensus": ("izzetprowessstandard",   "decks/izzet_prowess_standard.txt"),
}
GAMES = 200


def run_matchup(args):
    apl_key, deck_path, opp_name, opp_key, opp_path = args
    apl_a = get_match_apl(apl_key)
    apl_b = get_match_apl(opp_key)
    deck_a, _ = load_deck_from_file(deck_path)
    deck_b, _ = load_deck_from_file(opp_path)
    wins = 0
    for s in range(GAMES):
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b,
                          seed=s, on_play=(s % 2 == 0))
            if r.won:
                wins += 1
        except Exception:
            pass
    return apl_key, opp_name, wins


def main():
    jobs = []
    for label, (apl_key, dp) in DECKS.items():
        for opp_name, opp_key, opp_path, _ in FIELD:
            jobs.append((apl_key, dp, opp_name, opp_key, opp_path))

    print(f"\n{len(jobs)} jobs ({len(DECKS)} variants x {len(FIELD)} opps), N={GAMES}/each\n")
    results = {key: {} for _, (key, _) in DECKS.items()}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(run_matchup, j) for j in jobs]
        for f in as_completed(futs):
            apl_key, opp, w = f.result()
            results[apl_key][opp] = w

    nick_key = DECKS["Nick Tokyo"][0]
    pt_key   = DECKS["PT consensus"][0]
    print(f"{'Matchup':<22}  {'Tokyo':>8}  {'PT':>10}  {'Delta':>8}")
    print("-" * 60)
    for opp_name, _, _, _ in FIELD:
        n = results[nick_key].get(opp_name, 0) / GAMES * 100
        p = results[pt_key].get(opp_name, 0) / GAMES * 100
        d = n - p
        sign = '+' if d >= 0 else ''
        print(f"{opp_name:<22}  {n:>7.1f}%  {p:>9.1f}%  {sign}{d:>6.1f}pp")

    total_share = sum(s for _, _, _, s in FIELD)
    fw_n = sum((results[nick_key].get(name, 0) / GAMES) * s for name, _, _, s in FIELD) / total_share * 100
    fw_p = sum((results[pt_key].get(name, 0) / GAMES) * s for name, _, _, s in FIELD) / total_share * 100
    print()
    print(f"FW WR Nick Tokyo:   {fw_n:.1f}%")
    print(f"FW WR PT consensus: {fw_p:.1f}%")
    print(f"Delta:              {fw_n-fw_p:+.1f}pp")
    print(f"\nTotal: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
