"""Scout multiple underdog Standard archetypes against the field at 100g/matchup.

Tests each candidate's match APL through the same 15-archetype gauntlet,
returns FW WR for each. Top performers can then be validated at 500g.
"""
import sys, os, time
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FIELD_SHARE = {
    'Izzet Prowess':       0.245, 'Izzet Lessons':       0.118,
    'Izzet Spellementals': 0.078, 'Jeskai Control':      0.069,
    'Bant Rhythm':         0.049, 'Mono Green Landfall': 0.049,
    'Selesnya Landfall':   0.049, 'Bant Airbending':     0.039,
    'Sultai Reanimator':   0.029, 'Simic Rhythm':        0.029,
    'Gruul Aggro':         0.029, 'Selesnya Ouroboroid': 0.020,
    'Azorius High Noon':   0.015, 'Jeskai Lute':         0.030,
    'Dimir Excruciator':   0.080, 'Golgari Midrange':    0.040,
}
MATCHUPS = [
    ('Selesnya Landfall',   'selesnyalandfall',     'decks/selesnya_landfall_standard.txt'),
    ('Mono Green Landfall', 'monogreenlandfall',    'decks/mono_green_landfall_standard.txt'),
    ('Bant Airbending',     'bantairbending',       'decks/bant_airbending_standard.txt'),
    ('Bant Rhythm',         'bantrhythm',           'decks/bant_rhythm_standard.txt'),
    ('Simic Rhythm',        'simicrhythm',          'decks/simic_rhythm_standard.txt'),
    ('Sultai Reanimator',   'sultaireanimator',     'decks/sultai_reanimator_standard.txt'),
    ('Selesnya Ouroboroid', 'selesnyaouroboroid',   'decks/selesnya_ouroboroid_standard.txt'),
    ('Izzet Prowess',       'izzetprowessstandard', 'decks/izzet_prowess_standard.txt'),
    ('Izzet Lessons',       'izzetlesson',          'decks/izzet_lesson_standard.txt'),
    ('Izzet Spellementals', 'izzetspellementals',   'decks/izzet_spellementals_standard.txt'),
    ('Jeskai Control',      'jeskaicontrol',        'decks/jeskai_control_standard.txt'),
    ('Gruul Aggro',         'gruulaggro',           'decks/gruul_aggro_standard.txt'),
    ('Jeskai Lute',         'jeskailute',           'decks/jeskai_lute_standard.txt'),
    ('Dimir Excruciator',   'dimirexcruciator',     'decks/dimir_excruciator_standard.txt'),
    ('Golgari Midrange',    'golgarimidrange',      'decks/golgari_midrange_standard.txt'),
]

GAMES = 100
WORKERS = 8

# (label, apl_key, deck_file)
CANDIDATES = [
    ('Esper Pixie v2 (already known)', 'esperpixie',     'decks/esper_pixie_standard.txt'),
    ('Esper Raffine',                  'esperraffine',   'decks/esper_raffine_standard.txt'),
    ('Sultai Control',                 'sultaicontrol',  'decks/sultai_control_standard.txt'),
    ('Mardu Discard',                  'mardudiscard',   'decks/mardu_discard_standard.txt'),
    ('Four-Color Control',             'fourcolorcontrol','decks/four_color_control_standard.txt'),
    ('Four-Color Elemental',           'fourcolorelemental','decks/four_color_elemental_standard.txt'),
    ('Temur Omniscience',              'temuromniscience','decks/temur_omniscience_standard.txt'),
    ('Grixis Elementals',              'grixiselementals','decks/grixis_discard_standard.txt'),
    ('Temur Lute (own)',               'temurlute',      'decks/temur_lute_standard.txt'),
    ('Domain Ramp (sultai-rean APL)',  'domainramp',     'decks/domain_ramp_standard.txt'),
    ('Four-Color Overlords (auto APL)','fourcoloroverlords','decks/four_color_overlords_standard.txt'),
]


def _worker(args):
    name, key_a, deck_a, key_b, deck_b, n = args
    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match
    apl_a = get_match_apl(key_a)
    apl_b = get_match_apl(key_b)
    da, _ = load_deck_from_file(deck_a)
    db, _ = load_deck_from_file(deck_b)
    wins = 0
    for s in range(n):
        try:
            r = run_match(apl_a, da, apl_b, db, seed=s, on_play=s % 2 == 0)
            if r.won:
                wins += 1
        except Exception:
            pass
    return name, wins, n


def run_one(label, key_a, deck_a):
    jobs = [(name, key_a, deck_a, kb, df, GAMES) for (name, kb, df) in MATCHUPS]
    res = {}
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(_worker, j) for j in jobs]
        for f in as_completed(futs):
            n, w, t = f.result()
            res[n] = (w, t)
    total_share = sum(FIELD_SHARE.get(n, 0) for n in res)
    weighted = sum((w/t) * FIELD_SHARE.get(n, 0) for n, (w, t) in res.items())
    return (weighted/total_share*100) if total_share else 0, res


def main():
    print(f'=== RC DC underdog scout: {len(CANDIDATES)} candidates @ {GAMES}g/matchup ===')
    print()
    results = []
    for label, key, deck in CANDIDATES:
        if not os.path.exists(deck):
            print(f'[skip] {label}: missing {deck}')
            continue
        t0 = time.time()
        try:
            fwr, per = run_one(label, key, deck)
            elapsed = time.time() - t0
            results.append((label, fwr, per))
            # show worst 3 + best 3 matchups
            sorted_mu = sorted(per.items(), key=lambda x: x[1][0]/x[1][1])
            worst = ', '.join(f'{n} {int(w/t*100)}%' for n, (w, t) in sorted_mu[:2])
            best = ', '.join(f'{n} {int(w/t*100)}%' for n, (w, t) in sorted_mu[-2:])
            print(f'  {label:<35} FW {fwr:5.1f}%  ({elapsed:4.1f}s)  worst: [{worst}]  best: [{best}]')
        except Exception as e:
            print(f'  {label:<35} ERROR: {e}')
    print()
    print('=== Sorted ranking ===')
    for label, fwr, _ in sorted(results, key=lambda x: -x[1]):
        print(f'  {fwr:5.1f}%  {label}')


if __name__ == '__main__':
    main()
