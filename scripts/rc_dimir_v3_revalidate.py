"""500-game validation gauntlet for HN v2 (post-hill-climb).

Same 16 matchups, 500 games each, 8 workers parallel. Output to data/rc_hn_v2_final.txt.
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
DIMIR_DECK_FILE = 'decks/dimir_midrange_jermey_standard.txt'


def _worker(args):
    name, key_a, deck_a_file, key_b, deck_b_file, n_games = args
    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match

    apl_a = get_match_apl(key_a)
    apl_b = get_match_apl(key_b)
    deck_a, _ = load_deck_from_file(deck_a_file)
    deck_b, _ = load_deck_from_file(deck_b_file)
    wins = 0
    t0 = time.time()
    for s in range(n_games):
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b, seed=s, on_play=s % 2 == 0)
            if r.won:
                wins += 1
        except Exception:
            pass
    return name, wins, n_games, time.time() - t0


def main():
    print("Dimir Jermey v3 (re-validate post-Sunset-Saboteur fix) -- 15 matchups, 500 G1 each")
    print(f"Date: 2026-05-06  Format: PT SOS Standard + extras")
    print()
    jobs = [(name, 'dimirmidrangejermey', DIMIR_DECK_FILE, key_b, deck_file, GAMES)
            for (name, key_b, deck_file) in MATCHUPS]
    results = {}
    t_start = time.time()
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(_worker, j) for j in jobs]
        for fut in as_completed(futures):
            name, wins, total, dt = fut.result()
            results[name] = (wins, total, dt)
    print(f"{'Matchup':<35} {'WR':<5} {'share':<8} {'time':<6}")
    print('-' * 60)
    weighted = 0.0
    for name, _, _ in MATCHUPS:
        if name not in results:
            continue
        wins, total, dt = results[name]
        wr = wins / total
        share = FIELD_SHARE.get(name, 0)
        weighted += wr * share
        print(f"  {name:<28} {wins:>3}/{total} {int(wr*100):>3}%  {share*100:>4.1f}%  {dt:>6.1f}s")
    total_share = sum(FIELD_SHARE.get(n, 0) for n in results)
    fw_wr = (weighted / total_share * 100) if total_share else 0
    print()
    print('=' * 60)
    print(f"Field-weighted WR (over {total_share*100:.0f}% of field): {fw_wr:.1f}%")
    print(f"Total wall time: {time.time()-t_start:.1f}s ({WORKERS} workers)")


if __name__ == '__main__':
    main()
