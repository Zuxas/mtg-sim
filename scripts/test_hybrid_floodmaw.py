"""A/B test: replace Boomerang Basics with Into the Flood Maw in Hybrid.

User hypothesis: Into the Flood Maw is better per disruption-first
principle (instant speed catches opp threat as it lands, not next main).

Trade-off:
  Lose: self-bounce + draw, ETB re-trigger combo
  Gain: instant-speed disruption window
"""
import sys, os, time, json
from copy import deepcopy
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from concurrent.futures import ProcessPoolExecutor, as_completed
from apl import get_match_apl
from data.deck import load_deck_from_file
from data.card import Card
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


def make_flood_template():
    with open('data/rules_reference/scryfall_oracle_cards.json', encoding='utf-8') as f:
        cards = json.load(f)
    d = next(c for c in cards if c.get('name') == 'Into the Flood Maw')
    return Card(
        name=d['name'],
        mana_cost=d.get('mana_cost', '{U}'),
        cmc=float(d.get('cmc', 1)),
        type_line=d.get('type_line', 'Instant'),
        oracle_text=d.get('oracle_text', ''),
        colors=d.get('colors', ['U']),
    )


def build_floodmaw_variant(base_main, flood_template):
    deck = [deepcopy(c) for c in base_main if c.name != 'Boomerang Basics']
    n_cut = len(base_main) - len(deck)
    for _ in range(n_cut):
        deck.append(deepcopy(flood_template))
    return deck


def run_matchup(args):
    variant_name, deck_pickled, opp_name, opp_key, opp_path = args
    import pickle
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
    flood_template = make_flood_template()
    flood_deck = build_floodmaw_variant(base_main, flood_template)

    import pickle
    boomerang_pickled = pickle.dumps([deepcopy(c) for c in base_main])
    flood_pickled = pickle.dumps(flood_deck)

    n_boom = sum(1 for c in base_main if c.name == 'Boomerang Basics')
    n_flood = sum(1 for c in flood_deck if c.name == 'Into the Flood Maw')
    print(f'Base:    60 cards, {n_boom} Boomerang Basics')
    print(f'Variant: {len(flood_deck)} cards, {n_flood} Into the Flood Maw, 0 Boomerang')
    print()

    jobs = []
    for opp_name, opp_key, opp_path, _ in FIELD:
        jobs.append(('Boomerang', boomerang_pickled, opp_name, opp_key, opp_path))
        jobs.append(('FloodMaw',  flood_pickled,     opp_name, opp_key, opp_path))

    print(f'{len(jobs)} jobs, N={GAMES}/matchup\n')
    results = {'Boomerang': {}, 'FloodMaw': {}}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(run_matchup, j) for j in jobs]
        for f in as_completed(futs):
            v, opp, w = f.result()
            results[v][opp] = w

    # FW WR
    print(f"{'Matchup':<22}  {'Boomerang':>10}  {'FloodMaw':>10}  {'Delta':>8}")
    print('-' * 60)
    for opp_name, _, _, share in FIELD:
        b = results['Boomerang'][opp_name] / GAMES * 100
        f = results['FloodMaw'][opp_name] / GAMES * 100
        d = f - b
        sign = '+' if d >= 0 else ''
        print(f'{opp_name:<22}  {b:>9.1f}%  {f:>9.1f}%  {sign}{d:>6.1f}pp')

    total_share = sum(s for _, _, _, s in FIELD)
    fw_b = sum((results['Boomerang'][n]/GAMES) * s for n, _, _, s in FIELD) / total_share * 100
    fw_f = sum((results['FloodMaw'][n]/GAMES) * s for n, _, _, s in FIELD) / total_share * 100
    print()
    print(f'FW WR Boomerang: {fw_b:.1f}%')
    print(f'FW WR FloodMaw:  {fw_f:.1f}%')
    print(f'Delta:           {fw_f-fw_b:+.1f}pp')
    print(f'\\nTotal: {time.time()-t0:.1f}s')


if __name__ == '__main__':
    main()
