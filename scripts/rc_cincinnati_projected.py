"""RC Cincinnati projected meta gauntlet.

Builds a projected RC field by applying meta-shift logic to PT SOS:
  - Decks with PT WR > 55%: meta share boosted (people gravitate)
  - Decks in PT Top 8: large boost (especially Selesnya Landfall, won)
  - Decks with PT WR < 50% and most-played: drop (Prowess fatigue)
  - Post-PT-SOS emergent (Jeskai Lute): added at modest share
  - Current-meta archetypes that weren't at PT SOS but are real: kept

Logic:
  Selesnya Landfall: 3.3% PT * 4.0 (won + 2 in T8)            = ~13%
  Mono-Green Landfall: 18.6% PT * 1.4 (2 in T8, 55% WR)        = ~22%
  Selesnya Ouroboroid: low share * 3.0 (Nass T4, 65% WR)       = ~6%
  Izzet Lessons: 7.2% PT * 1.2 (cftsoc T4 + 45% overall)        = ~8%
  Izzet Spellementals: 7.8% PT * 1.1 (T8 + 51% WR)              = ~8%
  Azorius Tempo: 2.4% PT * 1.2 (T8 even at 44%)                = ~3%
  Izzet Prowess: 29.6% PT * 0.7 (most-played but flat)          = ~20%
  Bant Rhythm / Boros Dragons / Mardu Moonshadow: small boosts
  Jeskai Lute (post-PT emergent): 3% (Nakazima ReCQ list)
  Bant Airbending / Dimir Excruciator / others: from current meta
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from concurrent.futures import ProcessPoolExecutor, as_completed

# Projected RC Cincinnati shares (sum should be ~100%)
RC_CINCY_FIELD = [
    # archetype, apl_key, deck_file, projected_share
    ('Mono-Green Landfall',  'monogreenlandfall',    'decks/mono_green_landfall_standard.txt',   0.220),
    ('Izzet Prowess',        'izzetprowessstandard', 'decks/izzet_prowess_standard.txt',         0.200),
    ('Selesnya Landfall',    'selesnyalandfall',     'decks/selesnya_landfall_standard.txt',     0.130),
    ('Izzet Lessons',        'izzetlesson',          'decks/izzet_lesson_standard.txt',          0.080),
    ('Izzet Spellementals',  'izzetspellementals',   'decks/izzet_spellementals_standard.txt',   0.080),
    ('Selesnya Ouroboroid',  'selesnyaouroboroid',   'decks/selesnya_ouroboroid_standard.txt',   0.060),
    ('Bant Airbending',      'bantairbending',       'decks/bant_airbending_standard.txt',       0.040),
    ('Jeskai Control',       'jeskaicontrol',        'decks/jeskai_control_standard.txt',        0.040),
    ('Jeskai Lute',          'jeskailute',           'decks/jeskai_lute_standard.txt',           0.030),
    ('Azorius High Noon',    'azoriushighnoon',      'decks/azorius_high_noon_standard.txt',     0.030),
    ('Dimir Excruciator',    'dimirexcruciator',     'decks/dimir_excruciator_standard.txt',     0.030),
    ('Bant Rhythm',          'bantrhythm',           'decks/bant_rhythm_standard.txt',           0.020),
    ('Sultai Reanimator',    'sultaireanimator',     'decks/sultai_reanimator_standard.txt',     0.020),
    ('Boros Dragons',        'borosdragons',         'decks/boros_dragons_standard.txt',         0.015),
    ('Golgari Midrange',     'golgarimidrange',      'decks/golgari_midrange_standard.txt',      0.015),
    ('Gruul Aggro',          'gruulaggro',           'decks/gruul_aggro_standard.txt',           0.010),
    ('Simic Rhythm',         'simicrhythm',          'decks/simic_rhythm_standard.txt',          0.010),
]

# Shares are projection-based; we normalize at FW-WR computation time
TOTAL_SHARE = sum(s for _,_,_,s in RC_CINCY_FIELD)
assert 0.95 < TOTAL_SHARE < 1.10, f'Shares sum to {TOTAL_SHARE}, should be near 1.0'

CANDIDATES = [
    ('Hybrid (UB Bounce + Jermey)',  'dimirmidrangejermey', 'decks/dimir_bounce_jermey_hybrid_standard.txt'),
    ('Esper Pixie v2',               'esperpixie',          'decks/esper_pixie_standard.txt'),
    ('HN v2 (post-Warp APL)',        'azoriushighnoon',     'decks/azorius_high_noon_standard.txt'),
    ('Dimir Jermey v4',              'dimirmidrangejermey', 'decks/dimir_midrange_jermey_standard.txt'),
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
    for arch, kb, df, share in RC_CINCY_FIELD:
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
    for arch, _, _, share in RC_CINCY_FIELD:
        if arch not in res:
            continue
        wr = res[arch] / GAMES
        weighted += wr * share
        coverage += share
    return (weighted / coverage * 100) if coverage else 0, res


def main():
    print(f'RC Cincinnati projected meta gauntlet ({GAMES}g/matchup)')
    print(f'Field shares: {len(RC_CINCY_FIELD)} archetypes (sum {TOTAL_SHARE*100:.0f}%)')
    print()
    print(f'{"Archetype":<24}  {"Share":<7}')
    for arch, _, _, share in RC_CINCY_FIELD:
        print(f'  {arch:<22} {share*100:>5.1f}%')
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
    print()
    # Per-matchup matrix
    print('=== Per-matchup ===')
    print(f'  {"Matchup":<24}  {"share":<6}', end='')
    for label, _, _ in CANDIDATES:
        if label in all_results:
            print(f'  {label[:18]:<19}', end='')
    print()
    for arch, _, _, share in RC_CINCY_FIELD:
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
