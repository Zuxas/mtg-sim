"""Finish the 3 matchups missing from the prior smoke run -- SERIAL.

No ProcessPoolExecutor. 3 matchups x 30 games = 90 games total, fast enough.
Appends to data/lock_smoke_results.txt with flush after each result.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_matchup(name, key_a, deck_a_file, key_b, deck_b_file, n=30):
    print(f"[start ] {name}", flush=True)
    t0 = time.time()
    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match
    deck_a, _ = load_deck_from_file(deck_a_file)
    deck_b, _ = load_deck_from_file(deck_b_file)
    apl_a = get_match_apl(key_a)
    apl_b = get_match_apl(key_b)
    wins = 0
    errs = 0
    slow_games = []
    for s in range(n):
        g0 = time.time()
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b, seed=s, on_play=s % 2 == 0)
            if r.won:
                wins += 1
        except Exception as e:
            errs += 1
            if errs <= 2:
                print(f"  [err  ] seed={s}: {e!r}", flush=True)
        gt = time.time() - g0
        if gt > 5.0:
            slow_games.append((s, gt))
            print(f"  [slow ] seed={s} took {gt:.1f}s", flush=True)
    if slow_games:
        print(f"  [info ] {len(slow_games)} games >5s: {slow_games[:5]}", flush=True)
    dt = time.time() - t0
    print(f"[done  ] {name}  {wins}/{n}  errs={errs}  time={dt:.1f}s", flush=True)
    return wins, n, errs


def main():
    HN_KEY = 'azoriushighnoon'
    HN_DECK = 'decks/azorius_high_noon_standard.txt'
    # Run easiest first so we get SOME data even if a bad matchup hangs.
    matchups = [
        ('Selesnya Ouroboroid', HN_KEY, HN_DECK, 'selesnyaouroboroid',   'decks/selesnya_ouroboroid_standard.txt'),
        ('Izzet Spellementals', HN_KEY, HN_DECK, 'izzetspellementals',   'decks/izzet_spellementals_standard.txt'),
        ('Izzet Prowess',       HN_KEY, HN_DECK, 'izzetprowessstandard', 'decks/izzet_prowess_standard.txt'),
    ]

    out_path = "data/lock_smoke_results.txt"
    with open(out_path, "a", encoding="utf-8") as fout:
        fout.write("\n-- continuation: 3 missing matchups (serial) --\n")
        fout.flush()

        for (name, k1, p1, k2, p2) in matchups:
            try:
                wins, total, errs = run_matchup(name, k1, p1, k2, p2, n=30)
                wr = (wins / total * 100) if total else 0
                err_tag = f" [errs={errs}]" if errs else ""
                line = f"  {name:<26} {wins}/{total} ({wr:.0f}%){err_tag}\n"
            except Exception as e:
                line = f"  {name:<26} FATAL: {e!r}\n"
            fout.write(line)
            fout.flush()
            print(line, end="", flush=True)
    print(f"\nResults appended to {out_path}", flush=True)


if __name__ == "__main__":
    main()
