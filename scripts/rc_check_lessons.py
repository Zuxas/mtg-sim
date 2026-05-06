"""Quick re-check of HN vs Izzet Lessons after the inevitability-proxy fix.

Runs 30 games (matches the original sample size) so the result is comparable
to the prior 3/30 (10%) baseline.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match

    deck_a, _ = load_deck_from_file('decks/azorius_high_noon_standard.txt')
    deck_b, _ = load_deck_from_file('decks/izzet_lesson_standard.txt')
    apl_a = get_match_apl('azoriushighnoon')
    apl_b = get_match_apl('izzetlesson')

    print("[start] HN vs Izzet Lessons -- 30 games (post-fix)", flush=True)
    t0 = time.time()
    wins = 0
    for s in range(30):
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b, seed=s, on_play=s % 2 == 0)
            if r.won:
                wins += 1
        except Exception as e:
            print(f"  seed={s} ERR {e!r}", flush=True)
    dt = time.time() - t0
    pct = wins * 100 // 30
    print(f"[done ] {wins}/30 ({pct}%)  time={dt:.1f}s  (was 3/30 = 10%)",
          flush=True)


if __name__ == "__main__":
    main()
