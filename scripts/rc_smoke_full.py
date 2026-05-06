"""Re-run the full 12-matchup HN smoke after the Lessons proxy fix.

Serial. 30 games per matchup. Writes data/rc_smoke_full_results.txt with
per-matchup WR + field-weighted summary.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match

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
    ]

    # Approx PT SOS field shares (sum ~78% of field; rest = unmatched archetypes)
    field_share = {
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
    }

    apl_a = get_match_apl(HN_KEY)
    deck_a, _ = load_deck_from_file(HN_DECK)

    out_path = "data/rc_smoke_full_results.txt"
    with open(out_path, "w", encoding="utf-8") as fout:
        header = ("Azorius High Noon -- 12 matchups, 100 G1 each, post-fix baseline\n"
                  "Date: 2026-05-05  Format: PT SOS Standard\n\n"
                  f"{'Matchup':<26} {'WR':>10}   {'share':>6}   {'time':>6}\n"
                  + "-" * 60 + "\n")
        print(header, end="", flush=True)
        fout.write(header)
        fout.flush()

        results = {}
        grand_t0 = time.time()
        for (name, key_b, deck_b_file) in matchups:
            t0 = time.time()
            apl_b = get_match_apl(key_b)
            deck_b, _ = load_deck_from_file(deck_b_file)
            wins = 0
            errs = 0
            for s in range(100):
                try:
                    r = run_match(apl_a, deck_a, apl_b, deck_b,
                                  seed=s, on_play=s % 2 == 0)
                    if r.won:
                        wins += 1
                except Exception:
                    errs += 1
            dt = time.time() - t0
            wr_pct = wins / 100 * 100
            results[name] = (wins, 100, dt, errs)
            share = field_share.get(name, 0)
            err_tag = f" [errs={errs}]" if errs else ""
            line = (f"  {name:<24} {wins:>3}/{100} {wr_pct:>4.0f}%   "
                    f"{share*100:>4.1f}%   {dt:>5.1f}s{err_tag}\n")
            print(line, end="", flush=True)
            fout.write(line)
            fout.flush()

        # Field-weighted average
        total_share = sum(field_share.get(n, 0) for n, _ in results.items())
        weighted = sum((wins / total) * field_share.get(name, 0)
                       for name, (wins, total, _dt, _e) in results.items())
        fw_wr = (weighted / total_share * 100) if total_share else 0
        grand_dt = time.time() - grand_t0
        footer = ("\n" + "=" * 60 + "\n"
                  f"Field-weighted WR (over {total_share*100:.0f}% of field): "
                  f"{fw_wr:.1f}%\n"
                  f"Total runtime: {grand_dt:.1f}s\n")
        print(footer, end="", flush=True)
        fout.write(footer)


if __name__ == "__main__":
    main()
