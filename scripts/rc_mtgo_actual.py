"""Run candidates against the ACTUAL MTGO weekend meta shares.

Source: MTGO Standard RC Super Qualifier #12841317 + Sunday 2nd Chance PTQ
(both events 2026-05-03, day after PT SOS finished). 243 decks total.

This is meta DATA (not projection) -- it reflects what people actually
brought to those events. Note: Selesnya Landfall (PT winner) is only
2.5% here because players didn't have time to react. The Cincinnati
meta (a week or more after PT) will likely shift further toward
Selesnya Landfall + MGL.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from concurrent.futures import ProcessPoolExecutor, as_completed

# Real MTGO shares (243 decks, 2026-05-03)
# Format: (archetype_label, apl_key, deck_file, share)
MTGO_FIELD = [
    ('Izzet Prowess',         'izzetprowessstandard', 'decks/izzet_prowess_standard.txt',         0.169),
    ('Mono-Green Landfall',   'monogreenlandfall',    'decks/mono_green_landfall_standard.txt',   0.144),
    ('Izzet Spellementals',   'izzetspellementals',   'decks/izzet_spellementals_standard.txt',   0.091),
    ('Izzet Lessons',         'izzetlesson',          'decks/izzet_lesson_standard.txt',          0.082),
    ('Azorius Aggro',         'azoriusaggro',         'decks/azorius_aggro_standard.txt',         0.029),
    ('Selesnya Landfall',     'selesnyalandfall',     'decks/selesnya_landfall_standard.txt',     0.025),
    ('Azorius Blink',         'azoriusblink',         'decks/azorius_blink_standard.txt',         0.025),
    ('Temur Prowess',         'izzetprowessstandard', 'decks/izzet_prowess_standard.txt',         0.021),  # proxy
    ('Azorius Control',       'azoriuscontrol',       'decks/azorius_control_standard.txt',       0.021),
    ('Mardu Aggro',           'mardudiscard',         'decks/mardu_discard_standard.txt',         0.016),  # closest match
    ('Selesnya Ouroboroid',   'selesnyaouroboroid',   'decks/selesnya_ouroboroid_standard.txt',   0.012),  # +Gearhulk
    ('Jeskai Control',        'jeskaicontrol',        'decks/jeskai_control_standard.txt',        0.012),
    ('Dimir Excruciator',     'dimirexcruciator',     'decks/dimir_excruciator_standard.txt',     0.012),
    ('Azorius Flash',         'azoriushighnoon',      'decks/azorius_high_noon_standard.txt',     0.012),
    ('Bant Rhythm',           'bantrhythm',           'decks/bant_rhythm_standard.txt',           0.008),
]

CANDIDATES = [
    ('Hybrid (UB Bounce + Jermey)',  'dimirmidrangejermey', 'decks/dimir_bounce_jermey_hybrid_standard.txt'),
    ('Esper Pixie v2',               'esperpixie',          'decks/esper_pixie_standard.txt'),
    ('HN v2 (post-Warp)',            'azoriushighnoon',     'decks/azorius_high_noon_standard.txt'),
    ('Dimir Jermey v4',              'dimirmidrangejermey', 'decks/dimir_midrange_jermey_standard.txt'),
    ('Azorius Blink (itstime)',      'azoriusblink',        'decks/azorius_blink_standard.txt'),
    ('Linden Dimir Bounce',          'dimirmidrangejermey', 'decks/dimir_bounce_linden_standard.txt'),
]

GAMES = 200
WORKERS = 8


def _w(args):
    name, apl_a_key, deck_a, kb, df, n = args
    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match
    a = get_match_apl(apl_a_key)
    b = get_match_apl(kb)
    da, _ = load_deck_from_file(deck_a)
    db, _ = load_deck_from_file(df)
    wins = 0
    for s in range(n):
        try:
            r = run_match(a, da, b, db, seed=s, on_play=s % 2 == 0)
            if r.won:
                wins += 1
        except Exception:
            pass
    return name, wins


def run_one(label, apl_key, deck_path):
    jobs = []
    for arch, kb, df, share in MTGO_FIELD:
        if not os.path.exists(df):
            continue
        jobs.append((arch, apl_key, deck_path, kb, df, GAMES))
    res = {}
    with ProcessPoolExecutor(max_workers=WORKERS) as p:
        futs = [p.submit(_w, j) for j in jobs]
        for f in as_completed(futs):
            n, w = f.result()
            res[n] = w
    weighted = 0.0
    coverage = 0.0
    for arch, _, _, share in MTGO_FIELD:
        if arch not in res:
            continue
        wr = res[arch] / GAMES
        weighted += wr * share
        coverage += share
    return (weighted / coverage * 100) if coverage else 0, res


def main():
    total_share = sum(s for _,_,_,s in MTGO_FIELD)
    print(f'MTGO actual meta gauntlet ({GAMES}g/matchup, {total_share*100:.0f}% field coverage)')
    print(f'Source: MTGO RC SQ #12841317 + 2nd Chance PTQ, 2026-05-03, 243 decks')
    print()
    print(f'  {"Deck":<35}  FW WR')
    print('  ' + '-'*45)
    all_results = {}
    for label, apl, deck in CANDIDATES:
        if not os.path.exists(deck):
            continue
        t0 = time.time()
        fwr, per = run_one(label, apl, deck)
        all_results[label] = (fwr, per)
        print(f'  {label:<35}  {fwr:5.1f}%  ({time.time()-t0:.1f}s)')
    # Per-matchup
    print()
    print('=== Per-matchup (MTGO actual meta) ===')
    print(f'  {"Matchup":<24}  {"share":<6}', end='')
    for label, _, _ in CANDIDATES:
        if label in all_results:
            print(f'  {label[:18]:<19}', end='')
    print()
    for arch, _, _, share in MTGO_FIELD:
        print(f'  {arch:<22} {share*100:>5.1f}%', end='')
        for label, _, _ in CANDIDATES:
            if label in all_results:
                _, per = all_results[label]
                if arch in per:
                    wr = per[arch] / GAMES * 100
                    print(f'  {wr:>17.0f}% ', end='')
                else:
                    print(f'  {"--":>17}  ', end='')
        print()


if __name__ == '__main__':
    main()
