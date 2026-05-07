"""Esper Pixie baseline gauntlet for RC DC underdog candidate evaluation.

Same 15-archetype field as Dimir/HN gauntlets. 500 G1/matchup.
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
GAMES = 500
WORKERS = 8
DECK = 'decks/esper_pixie_standard.txt'


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
    t0 = time.time()
    for s in range(n):
        try:
            r = run_match(apl_a, da, apl_b, db, seed=s, on_play=s % 2 == 0)
            if r.won:
                wins += 1
        except Exception:
            pass
    return name, wins, n, time.time() - t0


def main():
    print("Esper Pixie baseline -- 15 matchups, 500 G1 each")
    print(f"Date: 2026-05-06")
    jobs = [(name, 'esperpixie', DECK, kb, df, GAMES) for (name, kb, df) in MATCHUPS]
    results = {}
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(_worker, j) for j in jobs]
        for f in as_completed(futs):
            n, w, t, dt = f.result()
            results[n] = (w, t, dt)
    print(f"{'Matchup':<35} {'WR':<5} {'share':<8} {'time':<6}")
    print('-' * 60)
    weighted = 0.0
    for name, _, _ in MATCHUPS:
        if name not in results:
            continue
        w, t, dt = results[name]
        wr = w / t
        share = FIELD_SHARE.get(name, 0)
        weighted += wr * share
        print(f"  {name:<28} {w:>3}/{t} {int(wr*100):>3}%  {share*100:>4.1f}%  {dt:>6.1f}s")
    total_share = sum(FIELD_SHARE.get(n, 0) for n in results)
    fw_wr = (weighted / total_share * 100) if total_share else 0
    print()
    print('=' * 60)
    print(f"Field-weighted WR (over {total_share*100:.0f}% of field): {fw_wr:.1f}%")


if __name__ == '__main__':
    main()
