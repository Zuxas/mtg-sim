"""A/B test: replace 4 Spyglass Siren with 4 Dream Beavers in Hybrid.

Pilot hypothesis (2026-05-08): Dream Beavers ({B} 1/1 flying ETB drain 1
+ scry 1) is better than Spyglass Siren ({U} 1/1 flying ETB Map token)
for fighting aggro on ladder. Life gain matters when getting cooked.

Uses the 24-land variant as the base (per prior pilot fix).
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


def build_24l_base(base_main):
    """Apply the 24L mana base fix from previous test."""
    deck = [deepcopy(c) for c in base_main]
    cuts = {"Multiversal Passage": 2, "Restless Reef": 1, "Long Goodbye": 1}
    templates = {n: next(deepcopy(c) for c in deck if c.name == n)
                 for n in ["Island", "Swamp", "Starting Town"]}
    new_deck = []
    for c in deck:
        if c.name in cuts and cuts[c.name] > 0:
            cuts[c.name] -= 1
        else:
            new_deck.append(c)
    new_deck.append(deepcopy(templates["Island"]))
    new_deck.append(deepcopy(templates["Swamp"]))
    new_deck.append(deepcopy(templates["Swamp"]))
    new_deck.append(deepcopy(templates["Starting Town"]))
    return new_deck


def swap_spyglass_for_beavers(deck):
    """Replace all 4 Spyglass Siren with 4 Dream Beavers."""
    # Get Dream Beavers template from another deck
    db_deck, _ = load_deck_from_file('decks/dimir_midrange_std_standard.txt')
    beaver_template = next(c for c in db_deck if c.name == 'Dream Beavers')

    new_deck = [deepcopy(c) for c in deck if c.name != 'Spyglass Siren']
    n_cut = len(deck) - len(new_deck)
    for _ in range(n_cut):
        new_deck.append(deepcopy(beaver_template))
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
    base_24l = build_24l_base(base_main)
    var_b = swap_spyglass_for_beavers(base_24l)

    n_spy_base = sum(1 for c in base_24l if c.name == 'Spyglass Siren')
    n_beaver_b = sum(1 for c in var_b if c.name == 'Dream Beavers')
    print(f"Base 24L:        {len(base_24l)} cards, {n_spy_base} Spyglass, 0 Beavers")
    print(f"Var B (4Bvr):    {len(var_b)} cards, 0 Spyglass, {n_beaver_b} Beavers")
    print()

    base_pickled = pickle.dumps(base_24l)
    var_pickled = pickle.dumps(var_b)

    jobs = []
    for opp_name, opp_key, opp_path, _ in FIELD:
        jobs.append(('Base 24L (Spyglass)', base_pickled, opp_name, opp_key, opp_path))
        jobs.append(('Var B (4 Beavers)',   var_pickled,  opp_name, opp_key, opp_path))

    print(f"{len(jobs)} jobs, N={GAMES}/each\n")
    results = {'Base 24L (Spyglass)': {}, 'Var B (4 Beavers)': {}}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(run_matchup, j) for j in jobs]
        for f in as_completed(futs):
            v, opp, w = f.result()
            results[v][opp] = w

    print(f"{'Matchup':<22}  {'Spyglass':>10}  {'Beavers':>10}  {'Delta':>8}")
    print("-" * 60)
    for opp_name, _, _, _ in FIELD:
        b = results['Base 24L (Spyglass)'][opp_name] / GAMES * 100
        v = results['Var B (4 Beavers)'][opp_name] / GAMES * 100
        d = v - b
        sign = '+' if d >= 0 else ''
        print(f"{opp_name:<22}  {b:>9.1f}%  {v:>9.1f}%  {sign}{d:>6.1f}pp")

    total_share = sum(s for _, _, _, s in FIELD)
    fw_b = sum((results['Base 24L (Spyglass)'][n]/GAMES) * s for n, _, _, s in FIELD) / total_share * 100
    fw_v = sum((results['Var B (4 Beavers)'][n]/GAMES) * s for n, _, _, s in FIELD) / total_share * 100
    print()
    print(f"FW WR Spyglass: {fw_b:.1f}%")
    print(f"FW WR Beavers:  {fw_v:.1f}%")
    print(f"Delta:          {fw_v-fw_b:+.1f}pp")
    print(f"\nTotal: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
