"""Dimir Bounce / Jermey hybrid gauntlet test."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from concurrent.futures import ProcessPoolExecutor, as_completed

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
DECK = 'decks/dimir_bounce_jermey_hybrid_standard.txt'
GAMES = 500


def _w(args):
    name, kb, df = args
    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match
    a = get_match_apl('dimirmidrangejermey')
    b = get_match_apl(kb)
    da, _ = load_deck_from_file(DECK)
    db, _ = load_deck_from_file(df)
    wins = 0
    t0 = time.time()
    for s in range(GAMES):
        try:
            r = run_match(a, da, b, db, seed=s, on_play=s % 2 == 0)
            if r.won: wins += 1
        except Exception:
            pass
    return name, wins, time.time() - t0


def main():
    print(f'Hybrid (UB Bounce + Jermey core) -- {GAMES}g/matchup')
    res = {}
    t = time.time()
    with ProcessPoolExecutor(max_workers=8) as p:
        futs = [p.submit(_w, j) for j in MATCHUPS]
        for f in as_completed(futs):
            n, w, dt = f.result()
            res[n] = (w, dt)
    for n, _, _ in MATCHUPS:
        if n in res:
            w, dt = res[n]
            sh = FIELD_SHARE.get(n, 0)
            print(f'  {n:<28} {w:>3}/{GAMES} {int(w/GAMES*100):>3}%  {sh*100:>4.1f}%  {dt:>5.1f}s')
    ts = sum(FIELD_SHARE.get(n, 0) for n in res)
    fwr = sum((w/GAMES)*FIELD_SHARE.get(n,0) for n,(w,_) in res.items())/ts*100
    print()
    print(f'Field-weighted WR: {fwr:.1f}%  ({time.time()-t:.1f}s)')


if __name__ == '__main__':
    main()
