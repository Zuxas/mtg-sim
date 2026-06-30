"""Bo3 sweep: Nick Tokyo Prowess vs 15-archetype Standard field, with SB plans applied.

Uses MATCHUP_SB_PLANS from the Tokyo APL when available, falls back to None.
Reports match WR per matchup and field-weighted match WR.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from concurrent.futures import ProcessPoolExecutor, as_completed
from apl import get_match_apl
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
N_MATCHES = 200


def run_one_matchup(args):
    apl_key, deck_path, opp_name, opp_key, opp_path = args
    apl_us = get_match_apl(apl_key)
    apl_opp = get_match_apl(opp_key)
    deck_us, sb_us = load_deck_from_file(deck_path)
    deck_opp, sb_opp = load_deck_from_file(opp_path)
    sb_plan_us = None
    if hasattr(apl_us, "MATCHUP_SB_PLANS"):
        sb_plan_us = apl_us.MATCHUP_SB_PLANS.get(opp_key)
    try:
        r = run_bo3_set(apl_us, deck_us, sb_us, apl_opp, deck_opp, sb_opp,
                        sb_plan_a=sb_plan_us, n=N_MATCHES, mix_play_draw=True,
                        n_workers=1)
        return apl_key, opp_name, r.match_wr_a(), r.g1_wr_a, r.g2_wr_a, r.g3_wr_a
    except Exception as e:
        return apl_key, opp_name, None, None, None, None


def main():
    decks = {
        "Nick Tokyo": "izzetprowessstandardtokyo",
        "PT consensus": "izzetprowessstandard",
    }
    deck_paths = {
        "izzetprowessstandardtokyo": "decks/izzet_prowess_nick_tokyo_standard.txt",
        "izzetprowessstandard": "decks/izzet_prowess_standard.txt",
    }
    jobs = []
    for label, key in decks.items():
        for opp_name, opp_key, opp_path, _ in FIELD:
            jobs.append((key, deck_paths[key], opp_name, opp_key, opp_path))

    print(f"\n{len(jobs)} Bo3 jobs, {N_MATCHES} matches each\n")
    results = {key: {} for key in decks.values()}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(run_one_matchup, j) for j in jobs]
        for f in as_completed(futs):
            apl_key, opp, mwr, g1, g2, g3 = f.result()
            if mwr is not None:
                results[apl_key][opp] = mwr
            else:
                results[apl_key][opp] = -1.0   # error sentinel

    nick = decks["Nick Tokyo"]
    pt   = decks["PT consensus"]
    print(f"{'Matchup':<22}  {'Tokyo':>8}  {'PT':>10}  {'Delta':>8}")
    print("-" * 60)
    for opp_name, _, _, _ in FIELD:
        n = results[nick].get(opp_name, -1.0)
        p = results[pt].get(opp_name, -1.0)
        n_str = f"{n:>7.1f}%" if n >= 0 else "    ERR"
        p_str = f"{p:>9.1f}%" if p >= 0 else "      ERR"
        d_str = f"{n-p:+7.1f}pp" if (n >= 0 and p >= 0) else "       --"
        print(f"{opp_name:<22}  {n_str}  {p_str}  {d_str}")

    # FW WR computed only over matchups where BOTH variants returned data
    paired = [(name, share) for name, _, _, share in FIELD
              if results[nick].get(name, -1) >= 0 and results[pt].get(name, -1) >= 0]
    paired_share = sum(s for _, s in paired)
    if paired_share > 0:
        fw_n = sum(results[nick][name]/100 * s for name, s in paired) / paired_share * 100
        fw_p = sum(results[pt][name]/100 * s for name, s in paired) / paired_share * 100
        print()
        print(f"Field coverage:           {paired_share:.1%} of meta ({len(paired)}/{len(FIELD)} matchups)")
        print(f"FW Match WR Nick Tokyo:   {fw_n:.1f}%")
        print(f"FW Match WR PT consensus: {fw_p:.1f}%")
        print(f"Delta:                    {fw_n-fw_p:+.1f}pp")
        # Per-matchup leaders
        wins = sum(1 for name, _ in paired if results[nick][name] > results[pt][name])
        ties = sum(1 for name, _ in paired if results[nick][name] == results[pt][name])
        losses = sum(1 for name, _ in paired if results[nick][name] < results[pt][name])
        print(f"Tokyo W/T/L vs PT:        {wins}-{ties}-{losses}")
    print(f"\nTotal: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
