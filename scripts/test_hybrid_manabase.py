"""Test Hybrid mana-base fix: 24 lands, fewer tapped.

Pilot feedback (2026-05-08): "not having the 24th land in this dimir
hybrid deck has killed me more than not, so many tapped lands too"

Sim doesn't model mana flood/screw distribution well, but we can still
verify the variant doesn't regress the FW WR baseline.

Variant changes vs base 23L:
  -2 Multiversal Passage  (always-tapped)
  -1 Restless Reef        (always-tapped, kept 1 for manland)
  -1 Long Goodbye         (cut 3-mana flex removal)
  +1 Island
  +1 Swamp
  +1 Starting Town        (untapped T1-3)
  +1 Swamp                (or Island; tested both via the Watery Grave swap)

Net: -3 always-tapped lands, +3 basics, +1 land total = 24 lands.
"""
import sys, os, time, pickle
from copy import deepcopy
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
APL_KEY = "dimirmidrangejermey"
GAMES = 500


def build_manabase_variant(base_main):
    """Apply the mana-base swap. Cuts: 2 Multiversal, 1 Restless Reef, 1 Long Goodbye.
    Adds: 1 Island, 1 Swamp, 1 Starting Town, 1 extra Swamp (net +1 land = 24)."""
    deck = [deepcopy(c) for c in base_main]
    cuts = {
        "Multiversal Passage": 2,
        "Restless Reef": 1,
        "Long Goodbye": 1,
    }
    # Templates from existing cards
    templates = {n: next(deepcopy(c) for c in deck if c.name == n)
                 for n in ["Island", "Swamp", "Starting Town"]}

    new_deck = []
    for c in deck:
        if c.name in cuts and cuts[c.name] > 0:
            cuts[c.name] -= 1
        else:
            new_deck.append(c)

    # Add the new lands
    new_deck.append(deepcopy(templates["Island"]))
    new_deck.append(deepcopy(templates["Swamp"]))
    new_deck.append(deepcopy(templates["Swamp"]))    # 2nd Swamp instead of duplicating something else
    new_deck.append(deepcopy(templates["Starting Town"]))

    # Remaining unmet cuts (in case of name mismatch) -- raise
    for n, remaining in cuts.items():
        if remaining > 0:
            raise ValueError(f"Couldn't cut {remaining} more of {n}")

    return new_deck


def run_matchup(args):
    variant_name, deck_pickled, opp_name, opp_key, opp_path = args
    deck_a = pickle.loads(deck_pickled)
    apl_a = get_match_apl(APL_KEY)
    apl_b = get_match_apl(opp_key)
    deck_b, _ = load_deck_from_file(opp_path)
    wins = 0
    for s in range(GAMES):
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b,
                          seed=s, on_play=(s % 2 == 0))
            if r.won: wins += 1
        except Exception:
            pass
    return variant_name, opp_name, wins


def main():
    base_main, _ = load_deck_from_file('decks/dimir_bounce_jermey_hybrid_standard.txt')
    variant_main = build_manabase_variant(base_main)

    base_lands = sum(1 for c in base_main if c.is_land())
    var_lands = sum(1 for c in variant_main if c.is_land())
    print(f"Base:    {len(base_main)} cards, {base_lands} lands")
    print(f"Variant: {len(variant_main)} cards, {var_lands} lands")
    print()
    print("Variant land breakdown:")
    from collections import Counter
    var_lands_count = Counter(c.name for c in variant_main if c.is_land())
    for name, q in sorted(var_lands_count.items(), key=lambda x: -x[1]):
        print(f"  {q} {name}")
    print()

    base_pickled = pickle.dumps([deepcopy(c) for c in base_main])
    var_pickled = pickle.dumps(variant_main)

    jobs = []
    for opp_name, opp_key, opp_path, _ in FIELD:
        jobs.append(('Base 23L', base_pickled, opp_name, opp_key, opp_path))
        jobs.append(('Var 24L',  var_pickled,  opp_name, opp_key, opp_path))

    print(f"{len(jobs)} matchup jobs, N={GAMES}/each\n")
    results = {'Base 23L': {}, 'Var 24L': {}}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(run_matchup, j) for j in jobs]
        for f in as_completed(futs):
            v, opp, w = f.result()
            results[v][opp] = w

    print(f"{'Matchup':<22}  {'Base 23L':>10}  {'Var 24L':>10}  {'Delta':>8}")
    print("-" * 60)
    for opp_name, _, _, share in FIELD:
        b = results['Base 23L'][opp_name] / GAMES * 100
        v = results['Var 24L'][opp_name] / GAMES * 100
        d = v - b
        sign = '+' if d >= 0 else ''
        print(f"{opp_name:<22}  {b:>9.1f}%  {v:>9.1f}%  {sign}{d:>6.1f}pp")

    total_share = sum(s for _, _, _, s in FIELD)
    fw_b = sum((results['Base 23L'][n]/GAMES) * s for n, _, _, s in FIELD) / total_share * 100
    fw_v = sum((results['Var 24L'][n]/GAMES) * s for n, _, _, s in FIELD) / total_share * 100
    print()
    print(f"FW WR Base 23L: {fw_b:.1f}%")
    print(f"FW WR Var 24L:  {fw_v:.1f}%")
    print(f"Delta:          {fw_v-fw_b:+.1f}pp")
    print(f"\nTotal: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
