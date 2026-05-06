"""Quick parallel smoke test for High Noon lock enforcement impact."""
import sys, os
from concurrent.futures import ProcessPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _run(args):
    name, key_a, deck_a_file, key_b, deck_b_file, n = args
    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match
    deck_a, _ = load_deck_from_file(deck_a_file)
    deck_b, _ = load_deck_from_file(deck_b_file)
    apl_a = get_match_apl(key_a)
    apl_b = get_match_apl(key_b)
    wins = 0
    for s in range(n):
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b, seed=s, on_play=s % 2 == 0)
            if r.won:
                wins += 1
        except Exception:
            pass
    return name, wins, n


def main():
    HN = ('azoriushighnoon', 'decks/azorius_high_noon_standard.txt')
    matchups = [
        ('Bant Airbending',     HN[0], HN[1], 'bantairbending',       'decks/bant_airbending_standard.txt'),
        ('Izzet Prowess',       HN[0], HN[1], 'izzetprowessstandard', 'decks/izzet_prowess_standard.txt'),
        ('Simic Rhythm',        HN[0], HN[1], 'simicrhythm',          'decks/simic_rhythm_standard.txt'),
        ('Izzet Lessons',       HN[0], HN[1], 'izzetlesson',          'decks/izzet_lesson_standard.txt'),
        ('Selesnya Landfall',   HN[0], HN[1], 'selesnyalandfall',     'decks/selesnya_landfall_standard.txt'),
        ('Mono Green Landfall', HN[0], HN[1], 'monogreenlandfall',    'decks/mono_green_landfall_standard.txt'),
        ('Izzet Spellementals', HN[0], HN[1], 'izzetspellementals',   'decks/izzet_spellementals_standard.txt'),
        ('Sultai Reanimator',   HN[0], HN[1], 'sultaireanimator',     'decks/sultai_reanimator_standard.txt'),
        ('Jeskai Control',      HN[0], HN[1], 'jeskaicontrol',        'decks/jeskai_control_standard.txt'),
        ('Selesnya Ouroboroid', HN[0], HN[1], 'selesnyaouroboroid',   'decks/selesnya_ouroboroid_standard.txt'),
        ('Bant Rhythm',         HN[0], HN[1], 'bantrhythm',           'decks/bant_rhythm_standard.txt'),
        ('Gruul Aggro',         HN[0], HN[1], 'gruulaggro',           'decks/gruul_aggro_standard.txt'),
    ]
    jobs = [(name, k1, p1, k2, p2, 30) for (name, k1, p1, k2, p2) in matchups]

    out_path = "data/lock_smoke_results.txt"
    with open(out_path, "w", encoding="utf-8") as fout:
        fout.write("Azorius High Noon -- 12 matchups, 30 G1 games each, lock enforcement WIRED\n\n")
        fout.write(f"{'Matchup':<28} {'WR':>8}\n")
        fout.write("-" * 40 + "\n")
        fout.flush()

        with ProcessPoolExecutor(max_workers=8) as pool:
            futs = {pool.submit(_run, j): j for j in jobs}
            for fut in as_completed(futs):
                name, wins, total = fut.result()
                wr = wins / total * 100 if total else 0
                line = f"  {name:<26} {wins}/{total} ({wr:.0f}%)\n"
                fout.write(line)
                fout.flush()
                print(line, end="", flush=True)
    print(f"\nResults written to {out_path}")


if __name__ == "__main__":
    main()
