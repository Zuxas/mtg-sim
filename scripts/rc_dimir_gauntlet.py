"""High-confidence Dimir Jermey gauntlet -- 13 matchups, 500 G1 each, parallel.

Field: PT SOS 12 decks + Zevin Faust's Azorius High Noon (we tuned today).
Special focus matchups for tuning:
  - Selesnya Landfall, Mono Green Landfall (Badgermole Cub ramp decks)
  - Bant Airbending (Cub variant)
  - Azorius High Noon (Zevin's prison-tempo)
"""
import sys, os, time
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Field shares: PT SOS roster + HN slotted in at conservative 1.5%
# (Zevin made T8 with it; some copycats expected at RCs)
FIELD_SHARE = {
    'Izzet Prowess':       0.245,
    'Izzet Lessons':       0.118,
    'Izzet Spellementals': 0.078,
    'Jeskai Control':      0.069,
    'Bant Rhythm':         0.049,
    'Mono Green Landfall': 0.049,
    'Selesnya Landfall':   0.049,
    'Bant Airbending':     0.039,
    'Sultai Reanimator':   0.029,
    'Simic Rhythm':        0.029,
    'Gruul Aggro':         0.029,
    'Selesnya Ouroboroid': 0.020,
    'Azorius High Noon':   0.015,   # Zevin Faust T8, expected slight uptick
}


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
    errs = 0
    t0 = time.time()
    for s in range(n_games):
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b,
                          seed=s, on_play=s % 2 == 0)
            if r.won:
                wins += 1
        except Exception:
            errs += 1
    dt = time.time() - t0
    return name, wins, n_games, errs, dt


def main():
    DIMIR_KEY = 'dimirmidrangejermey'
    DIMIR_DECK = 'decks/dimir_midrange_jermey_standard.txt'

    matchups = [
        # Landfall / Badgermole Cub block (key tuning target)
        ('Selesnya Landfall',   'selesnyalandfall',     'decks/selesnya_landfall_standard.txt'),
        ('Mono Green Landfall', 'monogreenlandfall',    'decks/mono_green_landfall_standard.txt'),
        ('Bant Airbending',     'bantairbending',       'decks/bant_airbending_standard.txt'),
        # Zevin Faust's HN (we tuned today; key tuning target)
        ('Azorius High Noon',   'azoriushighnoon',      'decks/azorius_high_noon_standard.txt'),
        # Other green ramp / midrange
        ('Bant Rhythm',         'bantrhythm',           'decks/bant_rhythm_standard.txt'),
        ('Simic Rhythm',        'simicrhythm',          'decks/simic_rhythm_standard.txt'),
        ('Sultai Reanimator',   'sultaireanimator',     'decks/sultai_reanimator_standard.txt'),
        ('Selesnya Ouroboroid', 'selesnyaouroboroid',   'decks/selesnya_ouroboroid_standard.txt'),
        # Spell-heavy / tempo / control
        ('Izzet Prowess',       'izzetprowessstandard', 'decks/izzet_prowess_standard.txt'),
        ('Izzet Lessons',       'izzetlesson',          'decks/izzet_lesson_standard.txt'),
        ('Izzet Spellementals', 'izzetspellementals',   'decks/izzet_spellementals_standard.txt'),
        ('Jeskai Control',      'jeskaicontrol',        'decks/jeskai_control_standard.txt'),
        # Aggro
        ('Gruul Aggro',         'gruulaggro',           'decks/gruul_aggro_standard.txt'),
    ]
    n_games = 500
    n_workers = 8

    out_path = "data/rc_dimir_gauntlet.txt"
    print(f"[start] Jermey Dimir vs {len(matchups)} matchups x {n_games} games  workers={n_workers}",
          flush=True)
    grand_t0 = time.time()
    results = {}

    jobs = [(name, DIMIR_KEY, DIMIR_DECK, key_b, deck_file, n_games)
            for (name, key_b, deck_file) in matchups]

    with open(out_path, "w", encoding="utf-8") as fout:
        header = ("Jermey Dimir Midrange -- 13 matchups, 500 G1 each, 8 workers parallel\n"
                  "Date: 2026-05-05  Format: PT SOS Standard + Azorius High Noon (Zevin)\n\n"
                  f"{'Matchup':<26} {'WR':>11}   {'share':>6}   {'time':>6}\n"
                  + "-" * 60 + "\n")
        print(header, end="", flush=True)
        fout.write(header)
        fout.flush()

        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            futures = {pool.submit(_worker, j): j[0] for j in jobs}
            for fut in as_completed(futures):
                name, wins, total, errs, dt = fut.result()
                wr_pct = wins / total * 100 if total else 0
                results[name] = (wins, total, dt, errs)
                share = FIELD_SHARE.get(name, 0)
                err_tag = f" [errs={errs}]" if errs else ""
                line = (f"  {name:<24} {wins:>4}/{total} {wr_pct:>4.0f}%   "
                        f"{share*100:>4.1f}%   {dt:>5.1f}s{err_tag}\n")
                print(line, end="", flush=True)
                fout.write(line)
                fout.flush()

        # Field-weighted summary
        total_share = sum(FIELD_SHARE.get(n, 0) for n in results)
        weighted = sum((wins / total) * FIELD_SHARE.get(name, 0)
                       for name, (wins, total, _dt, _e) in results.items())
        fw_wr = (weighted / total_share * 100) if total_share else 0

        # Tuning-target subset (Landfall/Cub/HN)
        targets = ['Selesnya Landfall', 'Mono Green Landfall',
                   'Bant Airbending', 'Azorius High Noon']
        target_total_share = sum(FIELD_SHARE.get(n, 0) for n in targets if n in results)
        target_weighted = sum((results[n][0] / results[n][1]) * FIELD_SHARE.get(n, 0)
                              for n in targets if n in results)
        target_fw = (target_weighted / target_total_share * 100) if target_total_share else 0

        grand_dt = time.time() - grand_t0
        footer = ("\n" + "=" * 60 + "\n"
                  f"Field-weighted WR (all {total_share*100:.0f}% of field): "
                  f"{fw_wr:.1f}%\n"
                  f"Tuning-target WR (Landfall/Cub/HN bloc, "
                  f"{target_total_share*100:.0f}% of field): "
                  f"{target_fw:.1f}%\n"
                  f"Total wall time: {grand_dt:.1f}s ({n_workers} workers)\n")
        print(footer, end="", flush=True)
        fout.write(footer)


if __name__ == "__main__":
    main()
