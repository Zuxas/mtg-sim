"""Verify 8 parallel workers don't blow up memory after today's bug fixes.

Runs 8 simultaneous workers, each doing 30 games of HN vs Spellementals
(the matchup that previously caused worker bloat). Expected: each worker
peaks around 600 MB and exits cleanly. Total system RAM should stay <8 GB.
"""
import sys, os, time
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _worker(worker_id):
    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match
    apl_a = get_match_apl('azoriushighnoon')
    apl_b = get_match_apl('izzetspellementals')
    deck_a, _ = load_deck_from_file('decks/azorius_high_noon_standard.txt')
    deck_b, _ = load_deck_from_file('decks/izzet_spellementals_standard.txt')
    wins = 0
    for s in range(30):
        seed = worker_id * 1000 + s
        r = run_match(apl_a, deck_a, apl_b, deck_b, seed=seed,
                       on_play=s % 2 == 0)
        if r.won:
            wins += 1
    try:
        import psutil
        rss = psutil.Process().memory_info().rss / (1024 * 1024)
    except ImportError:
        rss = -1
    return worker_id, wins, rss


def main():
    n_workers = 8
    print(f"[start] {n_workers} parallel workers x 30 games each", flush=True)
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        futures = [pool.submit(_worker, i) for i in range(n_workers)]
        for fut in as_completed(futures):
            wid, wins, rss = fut.result()
            rss_str = f"{rss:.0f} MB" if rss >= 0 else "(install psutil)"
            print(f"  worker {wid}: {wins}/30 wins  RSS at exit = {rss_str}",
                  flush=True)
    dt = time.time() - t0
    print(f"[done ] total wall time: {dt:.1f}s for {n_workers*30} games", flush=True)


if __name__ == "__main__":
    main()
