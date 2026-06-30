"""Bo3 sweep: 3 Looting variants vs the 15-archetype Standard field.

Compares:
  - izzetlootingstorechamp (Jermey Store Champ May 2026, locked)
  - izzetlootingportland   (Jermey Portland Feb 2026, field-tested 3-2)
  - izzetlootingmcnamara   (McNamara Spotlight Atlanta/Lyon Jan 2026)

Uses MATCHUP_SB_PLANS from the Looting match APL when available.
Reports match WR per matchup + field-weighted match WR per variant.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from concurrent.futures import ProcessPoolExecutor, as_completed
from apl import get_match_apl, APL_REGISTRY
from data.deck import load_deck_from_file
from engine.bo3_match import run_bo3_set


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
VARIANTS = ["izzetlootingstorechamp", "izzetlootingportland", "izzetlootingmcnamara"]
N_MATCHES = 200


def run_one_matchup(args):
    apl_key, opp_name, opp_key, opp_path = args
    apl_us = get_match_apl(apl_key)
    apl_opp = get_match_apl(opp_key)
    deck_path = APL_REGISTRY[apl_key][2]
    deck_us, sb_us = load_deck_from_file(deck_path)
    deck_opp, sb_opp = load_deck_from_file(opp_path)
    sb_plan_us = None
    if hasattr(apl_us, "MATCHUP_SB_PLANS"):
        sb_plan_us = apl_us.MATCHUP_SB_PLANS.get(opp_key)
    try:
        r = run_bo3_set(apl_us, deck_us, sb_us, apl_opp, deck_opp, sb_opp,
                        sb_plan_a=sb_plan_us, n=N_MATCHES, mix_play_draw=True,
                        n_workers=1)
        return apl_key, opp_name, r.match_wr_a()
    except Exception:
        return apl_key, opp_name, -1.0


def main():
    jobs = []
    for vk in VARIANTS:
        for opp_name, opp_key, opp_path, _ in FIELD:
            jobs.append((vk, opp_name, opp_key, opp_path))

    print(f"\n{len(jobs)} Bo3 jobs ({len(VARIANTS)} variants x {len(FIELD)} opps), N={N_MATCHES}/each\n")
    results = {vk: {} for vk in VARIANTS}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(run_one_matchup, j) for j in jobs]
        for f in as_completed(futs):
            vk, opp, mwr = f.result()
            results[vk][opp] = mwr

    labels = {"izzetlootingstorechamp": "StoreChp",
              "izzetlootingportland":   "Portland",
              "izzetlootingmcnamara":   "McNamara"}
    print(f"{'Matchup':<22} {labels[VARIANTS[0]]:>9} {labels[VARIANTS[1]]:>9} {labels[VARIANTS[2]]:>9}")
    print("-" * 60)
    for opp_name, _, _, _ in FIELD:
        cells = []
        for vk in VARIANTS:
            v = results[vk].get(opp_name, -1.0)
            cells.append(f"{v:>7.1f}%" if v >= 0 else "    ERR")
        print(f"{opp_name:<22} {cells[0]:>9} {cells[1]:>9} {cells[2]:>9}")

    print()
    for vk in VARIANTS:
        paired = [(name, share) for name, _, _, share in FIELD
                  if results[vk].get(name, -1) >= 0]
        ps = sum(s for _, s in paired)
        if ps > 0:
            fw = sum(results[vk][n]/100 * s for n, s in paired) / ps * 100
            print(f"FW Match WR {labels[vk]:<10}: {fw:.1f}%  (coverage {ps:.1%}, {len(paired)}/{len(FIELD)})")

    print(f"\nTotal: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
