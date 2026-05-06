"""Hill-climbing deck optimizer for Azorius High Noon (Zevin's PT-SOS T8 list).

Same pattern as scripts/hill_climb_dimir.py. Tests single-card swaps
against the live Standard meta. Accepts swaps that gain >= IMPROVE_THRESHOLD
field-weighted WR points.

HN's weakest matchups (baseline 57.5%):
  Gruul Aggro 20%, Simic Rhythm 31%, Selesnya Landfall 36%
Candidates target sweepers, removal flex, and mana stability.
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
# HN doesn't mirror itself in this gauntlet (would be 50/50 anyway)
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

HN_DECK_FILE = 'decks/azorius_high_noon_standard.txt'


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


BASIC_LANDS = {'Swamp', 'Island', 'Plains', 'Mountain', 'Forest'}


def apply_swap(main, swap):
    card_out, card_in, qty = swap
    new_main = Counter(main)
    if new_main.get(card_out, 0) < qty:
        return None
    new_main[card_out] -= qty
    if new_main[card_out] == 0:
        del new_main[card_out]
    new_main[card_in] = new_main.get(card_in, 0) + qty
    if new_main[card_in] > 4 and card_in not in BASIC_LANDS:
        return None
    if sum(new_main.values()) != 60:
        return None
    return new_main


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
    for s in range(n_games):
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b, seed=s, on_play=s % 2 == 0)
            if r.won:
                wins += 1
        except Exception:
            pass
    return name, wins, n_games


def run_gauntlet():
    jobs = [(name, 'azoriushighnoon', HN_DECK_FILE, key_b, deck_file,
             GAMES_PER_MATCHUP) for (name, key_b, deck_file) in MATCHUPS]
    results = {}
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(_worker, j) for j in jobs]
        for fut in as_completed(futures):
            name, wins, total = fut.result()
            results[name] = (wins, total)
    total_share = sum(FIELD_SHARE.get(n, 0) for n in results)
    weighted = sum((wins / total) * FIELD_SHARE.get(name, 0)
                   for name, (wins, total) in results.items())
    fw_wr = (weighted / total_share * 100) if total_share else 0
    return fw_wr, results


def main():
    # Candidate swaps, weakness-targeted
    # HN slots most likely to be flex: Spell Snare (2), Quantum Riddler (3),
    # Beza (1), Airbender Ascension (1), Restless Anchorage (1).
    # Targets: Avatar's Wrath (sweeper vs aggro), Get Lost (flex removal),
    #          Floodpits Drowner (already 4), basics (mana stability).
    candidates = [
        # Round 1: more sweepers vs aggro (Gruul 20%, Simic 31%)
        ('Quantum Riddler',    "Avatar's Wrath", 1),    # Wrath 2->3
        ('Beza, the Bounding Spring', "Avatar's Wrath", 1),
        ('Airbender Ascension', "Avatar's Wrath", 1),
        ('Spell Snare',        "Avatar's Wrath", 1),
        # Round 2: more flex removal
        ('Quantum Riddler',    'Get Lost', 1),           # Get Lost 2->3
        ('Beza, the Bounding Spring', 'Get Lost', 1),
        ('Airbender Ascension', 'Get Lost', 1),
        ('Spell Snare',        'Get Lost', 1),
        # Round 3: mana base — fewer utility lands, more basics for aggro consistency
        ('Restless Anchorage', 'Plains', 1),
        ('Multiversal Passage', 'Plains', 1),
        ('Abandoned Air Temple', 'Plains', 1),
        ('Restless Anchorage', 'Island', 1),
        # Round 4: 4th Quantum Riddler, drop singletons
        ('Beza, the Bounding Spring', 'Quantum Riddler', 1),
        ('Airbender Ascension', 'Quantum Riddler', 1),
        # Round 5: 3rd Spell Snare, drop singletons
        ('Beza, the Bounding Spring', 'Spell Snare', 1),
        ('Airbender Ascension', 'Spell Snare', 1),
        # Round 6: drop a Get Lost copy if not needed elsewhere
        # (only relevant after earlier rounds add Get Lost)
        ('Multiversal Passage', "Avatar's Wrath", 1),
        ('Abandoned Air Temple', 'Get Lost', 1),
    ]

    header_lines = []
    with open(HN_DECK_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('//'):
                header_lines.append(line.rstrip())
            else:
                break

    main_deck, sb = parse_deck(HN_DECK_FILE)
    print(f'[start] baseline deck: {sum(main_deck.values())} mainboard cards')

    backup_main = Counter(main_deck)
    backup_sb = Counter(sb)

    write_deck(HN_DECK_FILE, main_deck, sb, header_lines)
    print(f'[baseline] running gauntlet...', flush=True)
    t0 = time.time()
    baseline_wr, baseline_results = run_gauntlet()
    print(f'[baseline] FW WR = {baseline_wr:.2f}%  time={time.time()-t0:.1f}s', flush=True)

    best_wr = baseline_wr
    best_main = Counter(main_deck)
    accepted = []

    print()
    print(f'=== Hill-climbing {len(candidates)} candidate swaps (threshold +{IMPROVE_THRESHOLD}pp) ===')

    for i, swap in enumerate(candidates, 1):
        card_out, card_in, qty = swap
        trial_main = apply_swap(best_main, swap)
        if trial_main is None:
            print(f'  [{i:>2}] -{qty} {card_out:<28} +{qty} {card_in:<22} SKIP (invalid)', flush=True)
            continue
        write_deck(HN_DECK_FILE, trial_main, sb, header_lines)
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

    print()
    print('=== Final ===')
    write_deck(HN_DECK_FILE, best_main, sb, header_lines)
    print(f'  Baseline FW WR: {baseline_wr:.2f}%')
    print(f'  Final    FW WR: {best_wr:.2f}%  (delta: {best_wr-baseline_wr:+.2f}pp)')
    print(f'  Accepted swaps: {len(accepted)}')
    for (swap, wr) in accepted:
        print(f'    -{swap[2]} {swap[0]:<28} +{swap[2]} {swap[1]:<22} -> {wr:.2f}%')
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
