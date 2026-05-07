"""Run candidate decks against the PT Secrets of Strixhaven 2026 field.

Uses actual Day 1 field shares from data/pt_sos_2026.json. Different
from current-meta gauntlet because PT SOS was much more polarized:
Izzet Prowess 29.6% + MGL 18.6% + Spellementals 7.8% + Lessons 7.2%
= 63% of the field.
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from concurrent.futures import ProcessPoolExecutor, as_completed

# PT SOS field shares (computed from data/pt_sos_2026.json)
# Map archetype labels to (apl_key, deck_file, share)
PT_SOS_FIELD = [
    # archetype_name, apl_key, deck_file, players  (share = players/334)
    ('Izzet Prowess',        'izzetprowessstandard', 'decks/izzet_prowess_standard.txt',         99),
    ('Mono-Green Landfall',  'monogreenlandfall',    'decks/mono_green_landfall_standard.txt',   62),
    ('Izzet Spellementals',  'izzetspellementals',   'decks/izzet_spellementals_standard.txt',   26),
    ('Izzet Lessons',        'izzetlesson',          'decks/izzet_lesson_standard.txt',          24),
    ('Azorius Momo',         'azoriusmomo',          'decks/azorius_momo_standard.txt',          14),
    ('Jeskai Control',       'jeskaicontrol',        'decks/jeskai_control_standard.txt',        12),
    ('Selesnya Landfall',    'selesnyalandfall',     'decks/selesnya_landfall_standard.txt',     11),
    ('Izzet Maestro',        'izzetmaestro',         'decks/izzet_maestro_standard.txt',          9),
    ('Azorius Tempo',        'azoriustempo',         'decks/azorius_tempo_standard.txt',          8),
    ('Golgari Midrange',     'golgarimidrange',      'decks/golgari_midrange_standard.txt',       8),
    ('Dimir Excruciator',    'dimirexcruciator',     'decks/dimir_excruciator_standard.txt',      6),
    ('Sultai Control',       'sultaicontrol',        'decks/sultai_control_standard.txt',         5),
    ('Mardu Discard',        'mardudiscard',         'decks/mardu_discard_standard.txt',          3),
    ('Mono-Red Aggro',       'monoredaggro',         'decks/mono_red_aggro_standard.txt',         3),
    ('Selesnya Ouroboroid',  'selesnyaouroboroid',   'decks/selesnya_ouroboroid_standard.txt',    2),
    ('Simic Rhythm',         'simicrhythm',          'decks/simic_rhythm_standard.txt',           2),
    ('Bant Rhythm',          'bantrhythm',           'decks/bant_rhythm_standard.txt',            2),
]
TOTAL_PLAYERS = 334

# Decks to test
CANDIDATES = [
    ('Hybrid (UB Bounce + Jermey)', 'dimirmidrangejermey', 'decks/dimir_bounce_jermey_hybrid_standard.txt'),
    ('Esper Pixie v2',              'esperpixie',          'decks/esper_pixie_standard.txt'),
    ('HN v2 (post-Warp)',           'azoriushighnoon',     'decks/azorius_high_noon_standard.txt'),
    ('Dimir Jermey v4',             'dimirmidrangejermey', 'decks/dimir_midrange_jermey_standard.txt'),
    ('Linden Dimir Bounce',         'dimirmidrangejermey', 'decks/dimir_bounce_linden_standard.txt'),
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


def run_one(deck_label, apl_key, deck_path):
    """Run one candidate deck through the PT SOS field."""
    jobs = []
    for arch, kb, df, players in PT_SOS_FIELD:
        if not os.path.exists(df):
            continue
        jobs.append((arch, apl_key, deck_path, kb, df, GAMES))
    res = {}
    with ProcessPoolExecutor(max_workers=WORKERS) as p:
        futs = [p.submit(_w, j) for j in jobs]
        for f in as_completed(futs):
            n, w = f.result()
            res[n] = w
    # Compute FW WR using PT SOS shares
    weighted = 0.0
    total_share = 0.0
    for arch, _, _, players in PT_SOS_FIELD:
        if arch not in res:
            continue
        share = players / TOTAL_PLAYERS
        wr = res[arch] / GAMES
        weighted += wr * share
        total_share += share
    return (weighted / total_share * 100) if total_share else 0, res


def main():
    print(f'PT SOS gauntlet ({GAMES}g/matchup, PT Day 1 field shares)')
    print(f'Field: {len(PT_SOS_FIELD)} archetypes covering ~{sum(p for _,_,_,p in PT_SOS_FIELD)/TOTAL_PLAYERS*100:.0f}% of PT SOS\n')
    print(f'  {"Deck":<35}  FW WR')
    print('  ' + '-'*45)
    all_results = {}
    for label, apl, deck in CANDIDATES:
        if not os.path.exists(deck):
            print(f'  {label:<35}  SKIP (no deck file)')
            continue
        t0 = time.time()
        fwr, per = run_one(label, apl, deck)
        all_results[label] = (fwr, per)
        print(f'  {label:<35}  {fwr:5.1f}%  ({time.time()-t0:.1f}s)')
    # Per-matchup detail for the leader
    print()
    print('=== Per-matchup vs PT SOS field ===')
    print(f'  {"Matchup":<25}  {"share":<7}', end='')
    for label, _, _ in CANDIDATES:
        if label in all_results:
            print(f'  {label[:18]:<18}', end='')
    print()
    for arch, _, _, players in PT_SOS_FIELD:
        share = players / TOTAL_PLAYERS * 100
        print(f'  {arch:<25}  {share:>5.1f}%', end='')
        for label, _, _ in CANDIDATES:
            if label in all_results:
                _, per = all_results[label]
                if arch in per:
                    wr = per[arch] / GAMES * 100
                    print(f'  {wr:>16.0f}% ', end='')
                else:
                    print(f'  {"--":>16}  ', end='')
        print()


if __name__ == '__main__':
    main()
