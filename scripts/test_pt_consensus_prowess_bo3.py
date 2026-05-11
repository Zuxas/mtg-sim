"""Bo3 sweep: PT consensus Izzet Prowess vs the 15-archetype field.

Baseline for comparison vs Tokyo Prowess + Looting variants. This is the
"reference" Prowess list (PT SOS top finishers, pre-Tokyo updates).
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
US_KEY = "izzetprowessstandard"
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
        return apl_key, opp_name, r.match_wr_a(), bool(sb_plan_us)
    except Exception as e:
        return apl_key, opp_name, -1.0, False


def main():
    jobs = [(US_KEY, n, k, p) for n, k, p, _ in FIELD]
    print(f"\n{len(jobs)} Bo3 jobs (PT-consensus Prowess x {len(FIELD)} opps), N={N_MATCHES}\n")
    results = {}
    sb_used = {}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(run_one_matchup, j) for j in jobs]
        for f in as_completed(futs):
            vk, opp, mwr, sb_on = f.result()
            results[opp] = mwr
            sb_used[opp] = sb_on

    print(f"{'Matchup':<22} {'WR':>8s}  {'SB?':>4s}")
    print("-" * 42)
    for opp_name, _, _, _ in FIELD:
        v = results.get(opp_name, -1.0)
        sbflag = "YES" if sb_used.get(opp_name) else "no"
        cell = f"{v:>6.1f}%" if v >= 0 else "  ERR"
        print(f"{opp_name:<22} {cell:>8s}  {sbflag:>4s}")

    paired = [(name, share) for name, _, _, share in FIELD
              if results.get(name, -1) >= 0]
    ps = sum(s for _, s in paired)
    if ps > 0:
        fw = sum(results[n]/100 * s for n, s in paired) / ps * 100
        print(f"\nFW Match WR PT Consensus Prowess: {fw:.1f}%  ({len(paired)}/{len(FIELD)})")

    print(f"\nTotal: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
