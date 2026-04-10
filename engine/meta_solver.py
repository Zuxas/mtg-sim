"""
engine/meta_solver.py — Phase 3E meta solver

Given a metagame field, find the optimal deck and 75 configuration.
Runs every candidate deck against every field deck, computes
field-weighted win rates, and ranks decks by expected performance.

This is the "format solved" endgame — the equivalent of Stockfish
proving a forced win from a specific position. In MTG terms: given
this field, this is the best deck to register.

Usage:
    from engine.meta_solver import solve_meta, print_meta_report
    
    solution = solve_meta(
        candidate_decks={"Boros Energy": deck_a, "Izzet Prowess": deck_b},
        field_shares={"Boros Energy": 0.20, "Izzet Prowess": 0.10, ...},
        n_per_pair=1000
    )
    print_meta_report(solution)
"""

from __future__ import annotations
import time, os
from dataclasses import dataclass, field
from typing import Optional
from multiprocessing import Pool, freeze_support

from engine.match_engine import run_match
from apl.match_apl import GenericMatchAPL


@dataclass
class DeckScore:
    """Performance of one deck against the field."""
    name:           str
    field_wr:       float = 0.0        # field-weighted win rate
    matchup_wrs:    dict = field(default_factory=dict)  # {opp: wr}
    avg_kill_turn:  float = 0.0
    best_matchup:   str = ''
    worst_matchup:  str = ''


@dataclass
class MetaSolution:
    """Complete meta analysis result."""
    deck_scores:    list = field(default_factory=list)  # sorted by field_wr
    matchup_matrix: dict = field(default_factory=dict)  # {(a,b): wr_a}
    field_shares:   dict = field(default_factory=dict)
    n_per_pair:     int = 0
    total_games:    int = 0
    elapsed:        float = 0.0
    
    def best_deck(self) -> Optional[DeckScore]:
        return self.deck_scores[0] if self.deck_scores else None
    
    def get_matchup(self, deck_a: str, deck_b: str) -> float:
        return self.matchup_matrix.get((deck_a, deck_b), 0.5)


def _run_pair(args):
    """Worker: run N games between two decks. Returns (name_a, name_b, wins_a, wins_b, kill_turns)."""
    deck_a, deck_b, name_a, name_b, n, seed, apl_cls_a, apl_cls_b = args
    import random
    rng = random.Random(seed)
    
    # Instantiate APLs (can't pickle instances across processes)
    if apl_cls_a:
        apl_a = apl_cls_a()
    else:
        apl_a = GenericMatchAPL()
    if apl_cls_b:
        apl_b = apl_cls_b()
    else:
        apl_b = GenericMatchAPL()
    
    wins_a = 0
    wins_b = 0
    kill_turns = []
    
    for i in range(n):
        on_play = (i % 2 == 0)
        result = run_match(apl_a, deck_a, apl_b, deck_b,
                           on_play=on_play, seed=rng.randint(0, 999_999))
        if result.winner == 'a':
            wins_a += 1
        else:
            wins_b += 1
        kill_turns.append(result.kill_turn)
    
    return name_a, name_b, wins_a, wins_b, kill_turns


def solve_meta(candidate_decks: dict[str, list],
               field_shares: dict[str, float],
               n_per_pair: int = 1000,
               workers: int = None,
               seed: int = 42,
               apls: dict = None) -> MetaSolution:
    """
    Run every candidate deck against every other deck in the field.
    
    candidate_decks: {name: deck_list}
    field_shares: {name: meta_share}
    n_per_pair: games per matchup pair
    workers: parallel workers (default: cpu_count - 2)
    apls: {name: APL_class} — optional custom APL classes per deck
          (classes, not instances — they get instantiated in workers)
    """
    if workers is None:
        workers = min(20, max(1, os.cpu_count() - 2))
    
    import random
    rng = random.Random(seed)
    
    names = list(candidate_decks.keys())
    
    # Build all pairs
    pairs = []
    apl_map = apls or {}
    for i, name_a in enumerate(names):
        for j, name_b in enumerate(names):
            if i >= j:
                continue
            pairs.append((
                candidate_decks[name_a], candidate_decks[name_b],
                name_a, name_b, n_per_pair, rng.randint(0, 999_999),
                apl_map.get(name_a), apl_map.get(name_b),
            ))
    
    total_games = len(pairs) * n_per_pair
    print(f"  Meta solver: {len(names)} decks, {len(pairs)} pairs, "
          f"{total_games} total games across {workers} workers")
    
    t0 = time.time()
    
    # Run all pairs in parallel
    if workers > 1 and len(pairs) > 1:
        with Pool(workers) as pool:
            results = pool.map(_run_pair, pairs)
    else:
        results = [_run_pair(p) for p in pairs]
    
    elapsed = time.time() - t0
    
    # Build matchup matrix
    matrix = {}
    kill_data = {}
    for name_a, name_b, wins_a, wins_b, kill_turns in results:
        total = wins_a + wins_b
        wr_a = wins_a / total if total else 0.5
        matrix[(name_a, name_b)] = round(wr_a, 4)
        matrix[(name_b, name_a)] = round(1 - wr_a, 4)
        kill_data[(name_a, name_b)] = sum(kill_turns) / len(kill_turns) if kill_turns else 0
    
    # Mirror matchups = 50%
    for name in names:
        matrix[(name, name)] = 0.5
    
    # Compute field-weighted win rate for each deck
    deck_scores = []
    for name in names:
        matchup_wrs = {}
        weighted_sum = 0.0
        weight_total = 0.0
        
        for opp_name in names:
            if opp_name == name:
                continue
            wr = matrix.get((name, opp_name), 0.5)
            matchup_wrs[opp_name] = wr
            share = field_shares.get(opp_name, 0)
            weighted_sum += wr * share
            weight_total += share
        
        field_wr = weighted_sum / weight_total if weight_total > 0 else 0.5
        
        # Find best/worst matchups
        if matchup_wrs:
            best = max(matchup_wrs, key=matchup_wrs.get)
            worst = min(matchup_wrs, key=matchup_wrs.get)
        else:
            best = worst = ''
        
        deck_scores.append(DeckScore(
            name=name,
            field_wr=round(field_wr * 100, 1),
            matchup_wrs={k: round(v * 100, 1) for k, v in matchup_wrs.items()},
            best_matchup=best,
            worst_matchup=worst,
        ))
    
    # Sort by field-weighted win rate (best first)
    deck_scores.sort(key=lambda d: -d.field_wr)
    
    return MetaSolution(
        deck_scores=deck_scores,
        matchup_matrix=matrix,
        field_shares=field_shares,
        n_per_pair=n_per_pair,
        total_games=total_games,
        elapsed=round(elapsed, 1),
    )


def print_meta_report(solution: MetaSolution):
    """Print the full meta analysis report."""
    print(f"\n{'='*70}")
    print(f"  META SOLVER REPORT")
    print(f"  {len(solution.deck_scores)} decks, {solution.n_per_pair} games/pair, "
          f"{solution.total_games} total games in {solution.elapsed}s")
    print(f"{'='*70}")
    
    # Ranking table
    print(f"\n  {'Rank':<5} {'Deck':<25} {'Field WR':>8}  {'Best MU':>20}  {'Worst MU':>20}")
    print(f"  {'-'*5} {'-'*25} {'-'*8}  {'-'*20}  {'-'*20}")
    
    for i, ds in enumerate(solution.deck_scores):
        best_wr = ds.matchup_wrs.get(ds.best_matchup, 0)
        worst_wr = ds.matchup_wrs.get(ds.worst_matchup, 0)
        print(f"  {i+1:<5} {ds.name:<25} {ds.field_wr:>7.1f}%  "
              f"{ds.best_matchup[:15]:>15} {best_wr:.0f}%  "
              f"{ds.worst_matchup[:15]:>15} {worst_wr:.0f}%")
    
    # Matchup matrix
    names = [ds.name for ds in solution.deck_scores]
    short_names = [n[:12] for n in names]
    
    print(f"\n  MATCHUP MATRIX (row = deck, col = opponent, value = row's win %)")
    header = f"  {'':>14}"
    for sn in short_names:
        header += f" {sn:>12}"
    print(header)
    
    for ds in solution.deck_scores:
        row = f"  {ds.name[:14]:>14}"
        for opp in names:
            if opp == ds.name:
                row += f" {'--':>12}"
            else:
                wr = ds.matchup_wrs.get(opp, 50)
                row += f" {wr:>11.1f}%"
        print(row)
    
    # Recommendation
    best = solution.best_deck()
    if best:
        print(f"\n  RECOMMENDATION: Play {best.name} ({best.field_wr}% field WR)")
        print(f"    Best matchup: {best.best_matchup} ({best.matchup_wrs.get(best.best_matchup, 0):.0f}%)")
        print(f"    Worst matchup: {best.worst_matchup} ({best.matchup_wrs.get(best.worst_matchup, 0):.0f}%)")
    print()
