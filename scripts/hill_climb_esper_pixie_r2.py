"""Esper Pixie hill-climb ROUND 2 -- bounce-loop amplification.

The deck is a cheap-enchantment-bounce engine: Pixie/Kirin/Fear of Isolation
return enchantments to hand, you re-cast them for repeat ETB triggers
(Tinybones discard, Momentum Breaker sac, Nowhere to Run -3/-3, Stormchaser
Otter). Round 1 already optimized the "obviously cuttable" slots
(Bleachbone Verge, Cryogen Relic) and added 4th Concealed Courtyard,
+1 Tishana, +1 Siren.

Round 2: test going up on the engine cards (Stormchaser, Tinybones,
Fear of Isolation, Nowhere to Run, Momentum Breaker) by trimming the
non-loop pieces (Cecil 3rd, Kaito 3rd, Tragic Trajectory 3rd).
"""
import sys, os, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FIELD_SHARE = {
    'Izzet Prowess': 0.245, 'Izzet Lessons': 0.118, 'Izzet Spellementals': 0.078,
    'Jeskai Control': 0.069, 'Bant Rhythm': 0.049, 'Mono Green Landfall': 0.049,
    'Selesnya Landfall': 0.049, 'Bant Airbending': 0.039, 'Sultai Reanimator': 0.029,
    'Simic Rhythm': 0.029, 'Gruul Aggro': 0.029, 'Selesnya Ouroboroid': 0.020,
    'Azorius High Noon': 0.015, 'Jeskai Lute': 0.030, 'Dimir Excruciator': 0.080,
    'Golgari Midrange': 0.040,
}
MATCHUPS = [
    ('Selesnya Landfall', 'selesnyalandfall', 'decks/selesnya_landfall_standard.txt'),
    ('Mono Green Landfall', 'monogreenlandfall', 'decks/mono_green_landfall_standard.txt'),
    ('Bant Airbending', 'bantairbending', 'decks/bant_airbending_standard.txt'),
    ('Bant Rhythm', 'bantrhythm', 'decks/bant_rhythm_standard.txt'),
    ('Simic Rhythm', 'simicrhythm', 'decks/simic_rhythm_standard.txt'),
    ('Sultai Reanimator', 'sultaireanimator', 'decks/sultai_reanimator_standard.txt'),
    ('Selesnya Ouroboroid', 'selesnyaouroboroid', 'decks/selesnya_ouroboroid_standard.txt'),
    ('Izzet Prowess', 'izzetprowessstandard', 'decks/izzet_prowess_standard.txt'),
    ('Izzet Lessons', 'izzetlesson', 'decks/izzet_lesson_standard.txt'),
    ('Izzet Spellementals', 'izzetspellementals', 'decks/izzet_spellementals_standard.txt'),
    ('Jeskai Control', 'jeskaicontrol', 'decks/jeskai_control_standard.txt'),
    ('Gruul Aggro', 'gruulaggro', 'decks/gruul_aggro_standard.txt'),
    ('Jeskai Lute', 'jeskailute', 'decks/jeskai_lute_standard.txt'),
    ('Dimir Excruciator', 'dimirexcruciator', 'decks/dimir_excruciator_standard.txt'),
    ('Golgari Midrange', 'golgarimidrange', 'decks/golgari_midrange_standard.txt'),
]
GAMES = 100
WORKERS = 8
THRESHOLD = 0.5
DECK = 'decks/esper_pixie_standard.txt'
BASIC = {'Swamp', 'Island', 'Plains', 'Mountain', 'Forest'}


def parse(path):
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
            (sb if in_sb else main)[name] += qty
    return main, sb


def write(path, main, sb, header):
    with open(path, 'w', encoding='utf-8') as f:
        for h in header:
            f.write(h + '\n')
        for n in sorted(main):
            f.write(f'{main[n]} {n}\n')
        f.write('\nSideboard\n')
        for n in sorted(sb):
            f.write(f'{sb[n]} {n}\n')


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
    name, kb, df = args
    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match
    a = get_match_apl('esperpixie')
    b = get_match_apl(kb)
    da, _ = load_deck_from_file(DECK)
    db, _ = load_deck_from_file(df)
    wins = 0
    for s in range(GAMES):
        try:
            r = run_match(a, da, b, db, seed=s, on_play=s % 2 == 0)
            if r.won:
                wins += 1
        except Exception:
            pass
    return name, wins


def gauntlet():
    res = {}
    with ProcessPoolExecutor(max_workers=WORKERS) as p:
        futs = [p.submit(_worker, j) for j in MATCHUPS]
        for f in as_completed(futs):
            n, w = f.result()
            res[n] = w
    ts = sum(FIELD_SHARE.get(n, 0) for n in res)
    return sum((w/GAMES) * FIELD_SHARE.get(n, 0) for n, w in res.items()) / ts * 100


def main():
    # Round 2: amplify the bounce-loop engine
    candidates = [
        # +1 Stormchaser's Talent (3->4) by trimming non-loop pieces
        ('Cecil, Dark Knight',     "Stormchaser's Talent", 1),
        ("Kaito, Bane of Nightmares", "Stormchaser's Talent", 1),
        ('Tragic Trajectory',      "Stormchaser's Talent", 1),

        # +1 Tinybones Joins Up (2->3)
        ('Cecil, Dark Knight',     'Tinybones Joins Up', 1),
        ("Kaito, Bane of Nightmares", 'Tinybones Joins Up', 1),
        ('Tragic Trajectory',      'Tinybones Joins Up', 1),

        # +1 Fear of Isolation (1->2)
        ('Cecil, Dark Knight',     'Fear of Isolation', 1),
        ("Kaito, Bane of Nightmares", 'Fear of Isolation', 1),
        ('Tragic Trajectory',      'Fear of Isolation', 1),

        # +1 Nowhere to Run (3->4)
        ('Cecil, Dark Knight',     'Nowhere to Run', 1),
        ('Tragic Trajectory',      'Nowhere to Run', 1),

        # +1 Momentum Breaker (3->4)
        ('Cecil, Dark Knight',     'Momentum Breaker', 1),
        ('Tragic Trajectory',      'Momentum Breaker', 1),

        # +1 Tishana's Tidebinder (1->2)
        ('Cecil, Dark Knight',     "Tishana's Tidebinder", 1),
        ("Kaito, Bane of Nightmares", "Tishana's Tidebinder", 1),
        ('Tragic Trajectory',      "Tishana's Tidebinder", 1),

        # +1 Sunpearl Kirin already at 4 -- skip
        # +1 Cosmogrand already at 4 -- skip
    ]

    header = []
    with open(DECK, 'r') as f:
        for line in f:
            if line.startswith('//'):
                header.append(line.rstrip())
            else:
                break

    main_deck, sb = parse(DECK)
    backup = Counter(main_deck)
    print(f'[start] baseline: {sum(main_deck.values())} mainboard cards')

    write(DECK, main_deck, sb, header)
    print(f'[baseline] running gauntlet...', flush=True)
    t0 = time.time()
    base = gauntlet()
    print(f'[baseline] FW WR = {base:.2f}%  ({time.time()-t0:.1f}s)', flush=True)
    print()
    print(f'=== Round 2: {len(candidates)} bounce-loop amplification swaps ===')

    best = base
    best_main = Counter(main_deck)
    accepted = []
    for i, sw in enumerate(candidates, 1):
        out, inn, qty = sw
        trial = apply_swap(best_main, sw)
        if trial is None:
            print(f'  [{i:>2}] -{qty} {out:<28} +{qty} {inn:<25} SKIP', flush=True)
            continue
        write(DECK, trial, sb, header)
        t0 = time.time()
        wr = gauntlet()
        delta = wr - best
        verdict = 'ACCEPT' if delta >= THRESHOLD else 'reject'
        print(f'  [{i:>2}] -{qty} {out:<28} +{qty} {inn:<25} {wr:.2f}% ({delta:+.2f}pp) {time.time()-t0:.1f}s {verdict}', flush=True)
        if delta >= THRESHOLD:
            best = wr
            best_main = trial
            accepted.append((sw, wr))

    print()
    print('=== Final ===')
    write(DECK, best_main, sb, header)
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
