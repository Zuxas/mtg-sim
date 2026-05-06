"""Hill-climbing deck optimizer for Dimir Jermey v2.

Iteratively tests single-card swaps. For each candidate swap:
  1. Apply the swap to the working deck
  2. Run the parallel gauntlet (100 G1 / matchup, 15 matchups, 8 workers)
  3. Compute field-weighted WR
  4. Accept if FW WR improves by >= IMPROVE_THRESHOLD
  5. Otherwise revert

Continues until all candidates exhausted. Records trajectory.
"""
import sys, os, time, copy
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Field shares (real meta, ~97% coverage)
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
    ('Azorius High Noon',   'azoriushighnoon',      'decks/azorius_high_noon_standard.txt'),
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
IMPROVE_THRESHOLD = 0.5   # round 3: lower threshold to catch marginal wins

DIMIR_DECK_FILE = 'decks/dimir_midrange_jermey_standard.txt'


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


def write_deck(path, main, sb, header_lines=None):
    with open(path, 'w', encoding='utf-8') as f:
        if header_lines:
            for h in header_lines:
                f.write(h + '\n')
        for name in sorted(main):
            f.write(f'{main[name]} {name}\n')
        f.write('\nSideboard\n')
        for name in sorted(sb):
            f.write(f'{sb[name]} {name}\n')


def apply_swap(main, swap):
    """Apply (-card_out, +card_in, qty) swap. Returns new Counter or None if invalid."""
    card_out, card_in, qty = swap
    new_main = Counter(main)
    if new_main.get(card_out, 0) < qty:
        return None
    new_main[card_out] -= qty
    if new_main[card_out] == 0:
        del new_main[card_out]
    new_main[card_in] = new_main.get(card_in, 0) + qty
    if new_main[card_in] > 4:   # legal limit (ignoring basic lands)
        if card_in not in {'Swamp', 'Island', 'Plains', 'Mountain', 'Forest'}:
            return None
    if sum(new_main.values()) != 60:
        return None
    return new_main


def _worker(args):
    name, key_a, _deck_a_dummy, key_b, deck_b_file, n_games = args
    from apl import get_match_apl
    from data.deck import load_deck_from_file, load_deck_from_text
    from engine.match_runner import run_match

    apl_a = get_match_apl(key_a)
    apl_b = get_match_apl(key_b)
    # Load Dimir from current on-disk file (caller writes it before each round)
    deck_a, _ = load_deck_from_file(DIMIR_DECK_FILE)
    deck_b, _ = load_deck_from_file(deck_b_file)
    wins = 0
    for s in range(n_games):
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b, seed=s, on_play=s % 2 == 0)
            if r.won:
                wins += 1
        except Exception:
            pass
    return name, wins, n_games


def run_gauntlet():
    jobs = [(name, 'dimirmidrangejermey', DIMIR_DECK_FILE, key_b, deck_file,
             GAMES_PER_MATCHUP) for (name, key_b, deck_file) in MATCHUPS]
    results = {}
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(_worker, j) for j in jobs]
        for fut in as_completed(futures):
            name, wins, total = fut.result()
            results[name] = (wins, total)
    # FW WR
    total_share = sum(FIELD_SHARE.get(n, 0) for n in results)
    weighted = sum((wins / total) * FIELD_SHARE.get(name, 0)
                   for name, (wins, total) in results.items())
    fw_wr = (weighted / total_share * 100) if total_share else 0
    return fw_wr, results


def main():
    # Candidate swaps (single-card, -1 +1)
    # Format: (card_out, card_in, qty)
    candidates = [
        # Round 4: explore neighborhood of v3 (post-round-3 deck)
        # Going down on remaining 2-of "wash" cards
        ('Phantom Interference', 'Faebloom Trick', 1),       # 1 Phantom, 4 Faebloom
        ('Long Goodbye',         'Faebloom Trick', 1),       # 0 Long Goodbye, 4 Faebloom
        ('Phantom Interference', 'Bitter Triumph', 1),       # 1 Phantom, 4 Bitter
        ('Long Goodbye',         'Bitter Triumph', 1),       # 0 LG, 4 Bitter
        ('Restless Reef',        'Faebloom Trick', 1),       # 4 Faebloom
        ('Restless Reef',        'Bitter Triumph', 1),       # 4 Bitter
        ('Multiversal Passage',  'Faebloom Trick', 1),
        ('Multiversal Passage',  'Bitter Triumph', 1),
        ('Soulstone Sanctuary',  'Faebloom Trick', 1),
        ('Soulstone Sanctuary',  'Bitter Triumph', 1),
        # Try going up on Tishana (currently 3, stock 3.2) or Sunset Saboteur (1)
        ('Multiversal Passage',  'Tishana\'s Tidebinder', 1),# 4 Tishana
        ('Multiversal Passage',  'Sunset Saboteur', 1),      # 2 Saboteur
        ('Phantom Interference', 'Tishana\'s Tidebinder', 1),
        ('Long Goodbye',         'Tishana\'s Tidebinder', 1),
        # Threat density experiments
        ('Sunset Saboteur',      'Cecil, Dark Knight', 1),   # 4 Cecil, 0 Saboteur
        ('Malcolm, Alluring Scoundrel', 'Sunset Saboteur', 1), # 2 Saboteur instead of Malcolm
        ('Malcolm, Alluring Scoundrel', 'Cecil, Dark Knight', 1), # 4 Cecil
        ('Malcolm, Alluring Scoundrel', 'Faebloom Trick', 1),# 4 Faebloom
    ]

    # Read original header to preserve it
    header_lines = []
    with open(DIMIR_DECK_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('//'):
                header_lines.append(line.rstrip())
            else:
                break

    main_deck, sb = parse_deck(DIMIR_DECK_FILE)
    print(f'[start] baseline deck: {sum(main_deck.values())} mainboard cards')

    # Backup baseline
    backup_main = Counter(main_deck)
    backup_sb = Counter(sb)

    # Establish baseline FW WR
    write_deck(DIMIR_DECK_FILE, main_deck, sb, header_lines)
    print(f'[baseline] running gauntlet...', flush=True)
    t0 = time.time()
    baseline_wr, baseline_results = run_gauntlet()
    print(f'[baseline] FW WR = {baseline_wr:.2f}%  time={time.time()-t0:.1f}s', flush=True)

    best_wr = baseline_wr
    best_main = Counter(main_deck)
    accepted = []
    rejected = []

    print()
    print(f'=== Hill-climbing {len(candidates)} candidate swaps (threshold +{IMPROVE_THRESHOLD}pp) ===')

    for i, swap in enumerate(candidates, 1):
        card_out, card_in, qty = swap
        trial_main = apply_swap(best_main, swap)
        if trial_main is None:
            print(f'  [{i:>2}] -{qty} {card_out} +{qty} {card_in}  SKIP (invalid)', flush=True)
            continue
        write_deck(DIMIR_DECK_FILE, trial_main, sb, header_lines)
        t0 = time.time()
        trial_wr, _ = run_gauntlet()
        delta = trial_wr - best_wr
        dt = time.time() - t0
        verdict = 'ACCEPT' if delta >= IMPROVE_THRESHOLD else 'reject'
        print(f'  [{i:>2}] -{qty} {card_out:<28} +{qty} {card_in:<22} '
              f'{trial_wr:.2f}% ({delta:+.2f}pp) {dt:.1f}s  {verdict}', flush=True)
        if delta >= IMPROVE_THRESHOLD:
            best_wr = trial_wr
            best_main = trial_main
            accepted.append((swap, trial_wr))
        else:
            rejected.append((swap, trial_wr))

    # Write final winning deck
    print()
    print('=== Final ===')
    write_deck(DIMIR_DECK_FILE, best_main, sb, header_lines)
    print(f'  Baseline FW WR: {baseline_wr:.2f}%')
    print(f'  Final    FW WR: {best_wr:.2f}%  (delta: {best_wr-baseline_wr:+.2f}pp)')
    print(f'  Accepted swaps: {len(accepted)}')
    for (swap, wr) in accepted:
        print(f'    -{swap[2]} {swap[0]:<24} +{swap[2]} {swap[1]:<22} -> {wr:.2f}%')
    if best_main != backup_main:
        print()
        print('Final mainboard diff:')
        for c in set(list(backup_main) + list(best_main)):
            d = best_main.get(c, 0) - backup_main.get(c, 0)
            if d != 0:
                sign = '+' if d > 0 else ''
                print(f'  {sign}{d} {c}')


if __name__ == '__main__':
    main()
