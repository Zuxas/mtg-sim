"""Diagnose the spell-heavy lock matchup hang.

Runs ONE game of High Noon vs Izzet Spellementals. After 20s with no
completion, dumps the Python traceback to stderr so we see exactly where
the engine is stuck.
"""
import sys
import os
import faulthandler
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    # If the game runs >20s, dump traceback (engine should never need that long
    # for a single game — Selesnya Ouroboroid did 10 games in 2.8s).
    faulthandler.dump_traceback_later(20, file=sys.stderr, repeat=True)

    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match

    deck_a, _ = load_deck_from_file('decks/azorius_high_noon_standard.txt')
    deck_b, _ = load_deck_from_file('decks/selesnya_ouroboroid_standard.txt')
    apl_a = get_match_apl('azoriushighnoon')
    apl_b = get_match_apl('selesnyaouroboroid')

    print("[diag] running 30 games with per-game timing...", flush=True)
    overall_t0 = time.time()
    for s in range(30):
        t0 = time.time()
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b, seed=s, on_play=s % 2 == 0)
            dt = time.time() - t0
            won = "W" if r.won else "L"
            elapsed = time.time() - overall_t0
            print(f"  seed={s:>2} {won}  {dt:6.2f}s  total={elapsed:6.1f}s", flush=True)
        except Exception as e:
            dt = time.time() - t0
            print(f"  seed={s:>2} ERR  {dt:6.2f}s  {e!r}", flush=True)


if __name__ == "__main__":
    main()
