"""
engine/parallel_match.py — Parallel match simulation using all CPU cores.

Uses multiprocessing to run thousands of matches across workers.
Windows-safe: uses spawn context with proper __main__ guard.

Usage:
    from engine.parallel_match import run_parallel_matchup
    results = run_parallel_matchup(deck_a, deck_b, n=10000, workers=20)
"""
import os, random, time
from multiprocessing import Pool, freeze_support
from engine.match_engine import run_match
from apl.match_apl import GenericMatchAPL


def _worker(args):
    """Single worker: run a chunk of matches."""
    deck_a, deck_b, n, seed = args
    rng = random.Random(seed)
    apl_a = GenericMatchAPL()
    apl_b = GenericMatchAPL()
    
    wins_a = 0
    wins_b = 0
    kill_turns = []
    
    for i in range(n):
        on_play = (i % 2 == 0)
        game_seed = rng.randint(0, 999_999)
        result = run_match(apl_a, deck_a, apl_b, deck_b,
                           on_play=on_play, seed=game_seed)
        if result.winner == 'a':
            wins_a += 1
        else:
            wins_b += 1
        kill_turns.append(result.kill_turn)
    
    return wins_a, wins_b, kill_turns


def run_parallel_matchup(deck_a, deck_b, n=10000, workers=None, seed=42):
    """Run N matches in parallel across workers. Returns (win_pct_a, avg_turns, dist, elapsed)."""
    if workers is None:
        workers = min(20, max(1, os.cpu_count() - 2))
    
    chunk_size = n // workers
    rng = random.Random(seed)
    
    worker_args = [
        (deck_a, deck_b, chunk_size, rng.randint(0, 999_999))
        for _ in range(workers)
    ]
    
    t0 = time.time()
    with Pool(workers) as pool:
        results_list = pool.map(_worker, worker_args)
    elapsed = time.time() - t0
    
    total_a = sum(r[0] for r in results_list)
    total_b = sum(r[1] for r in results_list)
    all_turns = []
    for r in results_list:
        all_turns.extend(r[2])
    
    actual_total = total_a + total_b
    win_pct = round(total_a / actual_total * 100, 1)
    avg_turns = sum(all_turns) / len(all_turns)
    
    dist = {}
    for t in all_turns:
        dist[t] = dist.get(t, 0) + 1
    dist = {t: round(c / actual_total * 100, 1) for t, c in sorted(dist.items())}
    
    return win_pct, avg_turns, dist, elapsed, actual_total
