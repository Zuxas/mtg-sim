"""High-confidence parallel HN gauntlet -- 500 G1 games per matchup.

Uses 8 workers, each handling one full matchup. Total: 12 matchups x
500 games = 6000 games. Expected wall time ~30s on this machine.

Standard error at 500 games is ~2-3%, vs ~5% at 100 games. Suitable for
locking in a tournament-prep baseline.
"""
import sys, os, time
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# PT SOS field shares (~82% of full field; rest is fringe archetypes)
FIELD_SHARE = {
    'Izzet Prowess':       0.25,
    'Izzet Lessons':       0.12,
    'Selesnya Landfall':   0.05,
    'Mono Green Landfall': 0.05,
    'Izzet Spellementals': 0.08,
    'Bant Airbending':     0.04,
    'Bant Rhythm':         0.05,
    'Jeskai Control':      0.07,
    'Selesnya Ouroboroid': 0.02,
    'Sultai Reanimator':   0.03,
    'Simic Rhythm':        0.03,
    'Gruul Aggro':         0.03,
    'Jeskai Lute':         0.03,
    'Dimir Excruciator':   0.08,
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
    HN_KEY = 'azoriushighnoon'
    HN_DECK = 'decks/azorius_high_noon_standard.txt'
    matchups = [
        ('Izzet Prowess',       'izzetprowessstandard', 'decks/izzet_prowess_standard.txt'),
        ('Izzet Lessons',       'izzetlesson',          'decks/izzet_lesson_standard.txt'),
        ('Selesnya Landfall',   'selesnyalandfall',     'decks/selesnya_landfall_standard.txt'),
        ('Mono Green Landfall', 'monogreenlandfall',    'decks/mono_green_landfall_standard.txt'),
        ('Izzet Spellementals', 'izzetspellementals',   'decks/izzet_spellementals_standard.txt'),
        ('Bant Airbending',     'bantairbending',       'decks/bant_airbending_standard.txt'),
        ('Bant Rhythm',         'bantrhythm',           'decks/bant_rhythm_standard.txt'),
        ('Jeskai Control',      'jeskaicontrol',        'decks/jeskai_control_standard.txt'),
        ('Selesnya Ouroboroid', 'selesnyaouroboroid',   'decks/selesnya_ouroboroid_standard.txt'),
        ('Sultai Reanimator',   'sultaireanimator',     'decks/sultai_reanimator_standard.txt'),
        ('Simic Rhythm',        'simicrhythm',          'decks/simic_rhythm_standard.txt'),
        ('Gruul Aggro',         'gruulaggro',           'decks/gruul_aggro_standard.txt'),
        ('Jeskai Lute',         'jeskailute',           'decks/jeskai_lute_standard.txt'),
        ('Dimir Excruciator',   'dimirexcruciator',     'decks/dimir_excruciator_standard.txt'),
    ]
    n_games = 500
    n_workers = 8

    out_path = "data/rc_smoke_parallel_results.txt"
    print(f"[start] {len(matchups)} matchups x {n_games} games  workers={n_workers}",
          flush=True)
    grand_t0 = time.time()
    results = {}

    jobs = [(name, HN_KEY, HN_DECK, key_b, deck_file, n_games)
            for (name, key_b, deck_file) in matchups]

    with open(out_path, "w", encoding="utf-8") as fout:
        header = ("Azorius High Noon -- 12 matchups, 500 G1 each, 8 workers parallel\n"
                  "Date: 2026-05-05  Format: PT SOS Standard\n\n"
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
        grand_dt = time.time() - grand_t0
        footer = ("\n" + "=" * 60 + "\n"
                  f"Field-weighted WR (over {total_share*100:.0f}% of field): "
                  f"{fw_wr:.1f}%\n"
                  f"Total wall time: {grand_dt:.1f}s ({n_workers} workers)\n")
        print(footer, end="", flush=True)
        fout.write(footer)


if __name__ == "__main__":
    main()
