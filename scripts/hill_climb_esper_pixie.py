"""Hill-climbing optimizer for Esper Pixie (UWB tempo) -- RC DC underdog candidate.

Same pattern as hill_climb_hn.py and hill_climb_dimir.py. Tests single-card
swaps against current Standard meta. Threshold +0.5pp.
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

GAMES_PER_MATCHUP = 100
WORKERS = 8
IMPROVE_THRESHOLD = 0.5

DECK = 'decks/esper_pixie_standard.txt'


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
    db, _ = load_deck_from_file(deck_b)
    wins = 0
    for s in range(n):
        try:
            r = run_match(apl_a, deck_a, apl_b, db, seed=s, on_play=s % 2 == 0)
            if r.won:
                wins += 1
        except Exception:
            pass
    return name, wins, n


def run_gauntlet():
    jobs = [(name, 'esperpixie', kb, df, GAMES_PER_MATCHUP) for (name, kb, df) in MATCHUPS]
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
    # Candidate swaps. Targets: cut suspicious singletons / 2-ofs,
    # add staples like Long Goodbye / Bitter Triumph / Floodpits.
    # Also try going to 4-of on key cards.
    candidates = [
        # Round 1: cut singletons and small-count cards
        ('Bleachbone Verge', 'Watery Grave', 1),       # already 4 max -- INVALID, will skip
        ('Bleachbone Verge', 'Concealed Courtyard', 1),# 4th Courtyard
        ('Bleachbone Verge', 'Godless Shrine', 1),     # invalid -- already 4
        ('Bleachbone Verge', 'Swamp', 1),              # 2nd Swamp
        ('Fear of Isolation', 'Long Goodbye', 1),      # 1 LG
        ('Fear of Isolation', 'Bitter Triumph', 1),    # 1 Bitter
        ('Fear of Isolation', 'Floodpits Drowner', 1), # 1 Floodpits (UWB has UB lands)
        # Round 2: replace Cryogen Relic
        ('Cryogen Relic', 'Long Goodbye', 1),          # +1 LG
        ('Cryogen Relic', 'Bitter Triumph', 1),        # +1 Bitter
        ('Cryogen Relic', 'Floodpits Drowner', 1),     # +1 Floodpits
        ('Cryogen Relic', 'Tishana\'s Tidebinder', 1), # +1 Tishana
        # Round 3: replace Tinybones Joins Up
        ('Tinybones Joins Up', 'Long Goodbye', 1),
        ('Tinybones Joins Up', 'Bitter Triumph', 1),
        ('Tinybones Joins Up', 'Floodpits Drowner', 1),
        ('Tinybones Joins Up', 'Tishana\'s Tidebinder', 1),
        # Round 4: 4th of key cards
        ('Cryogen Relic', 'Cecil, Dark Knight', 1),    # 4th Cecil
        ('Cryogen Relic', 'Spyglass Siren', 1),        # 4th Siren
        ('Cryogen Relic', 'Stormchaser\'s Talent', 1), # 4th Stormchaser
        ('Cryogen Relic', 'Tragic Trajectory', 1),     # 4th Tragic
        ('Tinybones Joins Up', 'Cecil, Dark Knight', 1),
        ('Tinybones Joins Up', 'Spyglass Siren', 1),
        ('Tinybones Joins Up', 'Stormchaser\'s Talent', 1),
        # Round 5: try cutting Momentum Breaker (3) for staples
        ('Momentum Breaker', 'Long Goodbye', 1),
        ('Momentum Breaker', 'Bitter Triumph', 1),
        ('Momentum Breaker', 'Floodpits Drowner', 1),
        # Round 6: try cutting Nowhere to Run (3) -- check value
        ('Nowhere to Run', 'Long Goodbye', 1),
        ('Nowhere to Run', 'Bitter Triumph', 1),
        ('Nowhere to Run', 'Tishana\'s Tidebinder', 1),
    ]

    header = []
    with open(DECK, 'r') as f:
        for line in f:
            if line.startswith('//'):
                header.append(line.rstrip())
            else:
                break

    main_deck, sb = parse_deck(DECK)
    backup = Counter(main_deck)
    print(f'[start] baseline: {sum(main_deck.values())} mainboard cards')

    write_deck(DECK, main_deck, sb, header)
    print('[baseline] running gauntlet...', flush=True)
    t0 = time.time()
    base = run_gauntlet()
    print(f'[baseline] FW WR = {base:.2f}%  ({time.time()-t0:.1f}s)', flush=True)

    best = base
    best_main = Counter(main_deck)
    accepted = []

    print()
    print(f'=== Hill-climbing {len(candidates)} candidates (threshold +{IMPROVE_THRESHOLD}pp) ===')

    for i, sw in enumerate(candidates, 1):
        out, inn, qty = sw
        trial = apply_swap(best_main, sw)
        if trial is None:
            print(f'  [{i:>2}] -{qty} {out:<28} +{qty} {inn:<25} SKIP', flush=True)
            continue
        write_deck(DECK, trial, sb, header)
        t0 = time.time()
        wr = run_gauntlet()
        delta = wr - best
        verdict = 'ACCEPT' if delta >= IMPROVE_THRESHOLD else 'reject'
        print(f'  [{i:>2}] -{qty} {out:<28} +{qty} {inn:<25} {wr:.2f}% ({delta:+.2f}pp) {time.time()-t0:.1f}s {verdict}', flush=True)
        if delta >= IMPROVE_THRESHOLD:
            best = wr
            best_main = trial
            accepted.append((sw, wr))

    print()
    print('=== Final ===')
    write_deck(DECK, best_main, sb, header)
    print(f'  Baseline FW WR: {base:.2f}%')
    print(f'  Final    FW WR: {best:.2f}%  (delta: {best-base:+.2f}pp)')
    print(f'  Accepted swaps: {len(accepted)}')
    for (sw, wr) in accepted:
        print(f'    -{sw[2]} {sw[0]:<24} +{sw[2]} {sw[1]:<22} -> {wr:.2f}%')
    if best_main != backup:
        print()
        print('Final mainboard diff:')
        for c in set(list(backup) + list(best_main)):
            d = best_main.get(c, 0) - backup.get(c, 0)
            if d != 0:
                sign = '+' if d > 0 else ''
                print(f'  {sign}{d} {c}')


if __name__ == '__main__':
    main()
