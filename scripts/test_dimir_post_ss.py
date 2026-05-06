"""Targeted test: cut the 1 Sunset Saboteur from Dimir v3 for replacements.

Tests several -1 SS / +1 X swaps at 100g/matchup. Reports which swaps
recover the most WR. After SS attack-trigger fix, SS is now a 4/1 that
buffs opp creatures on attack -- might be a net negative.
"""
import sys, os, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import Counter

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
DECK = 'decks/dimir_midrange_jermey_standard.txt'


def parse_deck(path):
    main, sb = Counter(), Counter()
    in_sb = False
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            if line.lower().startswith('sideboard'):
                in_sb = True
                continue
            parts = line.split(' ', 1)
            if len(parts) != 2 or not parts[0].isdigit():
                continue
            qty = int(parts[0])
            name = parts[1].strip()
            if in_sb:
                sb[name] += qty
            else:
                main[name] += qty
    return main, sb


def write_deck(path, main, sb, header):
    with open(path, 'w', encoding='utf-8') as f:
        for h in header:
            f.write(h + '\n')
        for name in sorted(main):
            f.write(f'{main[name]} {name}\n')
        f.write('\nSideboard\n')
        for name in sorted(sb):
            f.write(f'{sb[name]} {name}\n')


BASIC = {'Swamp', 'Island', 'Plains', 'Mountain', 'Forest'}


def apply_swap(main, swap):
    out, inn, qty = swap
    new = Counter(main)
    if new.get(out, 0) < qty:
        return None
    new[out] -= qty
    if new[out] == 0:
        del new[out]
    new[inn] = new.get(inn, 0) + qty
    if new[inn] > 4 and inn not in BASIC:
        return None
    if sum(new.values()) != 60:
        return None
    return new


def _worker(args):
    name, key_a, key_b, deck_b, n = args
    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match
    apl_a = get_match_apl(key_a)
    apl_b = get_match_apl(key_b)
    deck_a, _ = load_deck_from_file(DECK)
    deck_bb, _ = load_deck_from_file(deck_b)
    wins = 0
    for s in range(n):
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_bb, seed=s, on_play=s % 2 == 0)
            if r.won:
                wins += 1
        except Exception:
            pass
    return name, wins, n


def run_gauntlet():
    jobs = [(name, 'dimirmidrangejermey', kb, df, GAMES) for (name, kb, df) in MATCHUPS]
    res = {}
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(_worker, j) for j in jobs]
        for f in as_completed(futs):
            n, w, t = f.result()
            res[n] = (w, t)
    total_share = sum(FIELD_SHARE.get(n, 0) for n in res)
    weighted = sum((w/t) * FIELD_SHARE.get(n, 0) for n, (w, t) in res.items())
    return (weighted/total_share*100) if total_share else 0


def main():
    header = []
    with open(DECK, 'r') as f:
        for line in f:
            if line.startswith('//'):
                header.append(line.rstrip())
            else:
                break

    main_deck, sb = parse_deck(DECK)
    backup = Counter(main_deck)

    # Targeted: -1 SS, +1 X candidates
    candidates = [
        ('Sunset Saboteur', 'Cecil, Dark Knight', 1),         # 4 Cecil
        ('Sunset Saboteur', 'Faebloom Trick', 1),             # 4 Faebloom
        ('Sunset Saboteur', 'Floodpits Drowner', 1),          # 4 Floodpits
        ('Sunset Saboteur', 'Bitter Triumph', 1),             # 4 Bitter
        ('Sunset Saboteur', 'Long Goodbye', 1),               # 2 Long Goodbye
        ('Sunset Saboteur', 'Phantom Interference', 1),       # 3 Phantom
        ('Sunset Saboteur', "Tishana's Tidebinder", 1),       # 4 Tishana
        ('Sunset Saboteur', 'Swamp', 1),                      # 6 Swamp (more lands)
        ('Sunset Saboteur', 'Island', 1),                     # 6 Island
    ]

    # Baseline
    write_deck(DECK, main_deck, sb, header)
    print(f'[baseline (post-SS-fix)] running gauntlet...', flush=True)
    t0 = time.time()
    base = run_gauntlet()
    print(f'[baseline] FW WR = {base:.2f}%  ({time.time()-t0:.1f}s)', flush=True)
    print()
    print(f'=== Testing {len(candidates)} -1 Sunset Saboteur swaps ===')

    best = base
    best_main = Counter(main_deck)
    best_swap = None
    for i, sw in enumerate(candidates, 1):
        out, inn, qty = sw
        trial = apply_swap(best_main, sw)
        if trial is None:
            print(f'  [{i}] -{qty} {out} +{qty} {inn} SKIP', flush=True)
            continue
        write_deck(DECK, trial, sb, header)
        t0 = time.time()
        wr = run_gauntlet()
        delta = wr - base
        verdict = 'BEST' if wr > best else ('OK' if delta >= 0 else 'reject')
        if wr > best:
            best = wr
            best_main = trial
            best_swap = sw
        print(f'  [{i}] -{qty} {out:<22} +{qty} {inn:<25} {wr:.2f}% ({delta:+.2f}pp) {verdict}', flush=True)

    # Restore original
    write_deck(DECK, backup, sb, header)
    print()
    print('=== Result ===')
    print(f'  Baseline (with 1 SS):      {base:.2f}%')
    print(f'  Best swap:                 {best:.2f}% ({best - base:+.2f}pp)')
    if best_swap:
        out, inn, qty = best_swap
        print(f'  Best:  -{qty} {out}, +{qty} {inn}')
        print()
        print('  (Deck file restored to baseline. To apply, manually swap.)')
    else:
        print('  No swap improved on baseline.')


if __name__ == '__main__':
    main()
