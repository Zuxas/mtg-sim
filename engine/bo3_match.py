"""
engine/bo3_match.py — Best-of-3 using the real match engine (Phase 3A)

Runs actual games for all three games, with real sideboarding between games.
Uses engine/match_engine.py for game simulation and engine/sideboard.py
for card swaps between games.

Key differences from old bo3.py:
  - OLD: goldfish race comparison + heuristic sb_premium
  - NEW: actual two-player games with combat, blocking, interaction
  - OLD: G2/G3 win rate estimated from G1 + flat bonus
  - NEW: G2/G3 played with actual sideboarded decks

Usage:
    from engine.bo3_match import run_bo3, run_bo3_set, print_bo3_report
    result = run_bo3(apl_a, deck_a, sb_a, apl_b, deck_b, sb_b,
                     sb_plan_a=("vs Prowess", in_a, out_a),
                     sb_plan_b=("vs Boros", in_b, out_b))
"""

from __future__ import annotations
import random
import concurrent.futures
from dataclasses import dataclass, field
from copy import deepcopy
from typing import Optional

from engine.match_engine import run_match
from engine.match_state import MatchResult
from engine.sideboard import apply_sideboard_plan, parse_sb_string
from apl.match_apl import MatchAPL


@dataclass
class Bo3MatchResult:
    """Result of a single Best-of-3 match."""
    winner:         str = ''        # 'a' or 'b'
    games_won_a:    int = 0
    games_won_b:    int = 0
    game_results:   list = field(default_factory=list)  # list of MatchResult
    total_turns:    int = 0
    went_to_g3:     bool = False

    def match_score(self) -> str:
        return f"{self.games_won_a}-{self.games_won_b}"


@dataclass
class Bo3SetResults:
    """Aggregated results from N Bo3 matches."""
    n_matches:      int = 0
    a_wins:         int = 0
    b_wins:         int = 0
    g3_rate:        float = 0.0     # % of matches that went to game 3
    avg_total_turns: float = 0.0
    g1_wr_a:        float = 0.0     # game 1 win rate for player A
    g2_wr_a:        float = 0.0     # game 2 win rate for player A (post-board)
    g3_wr_a:        float = 0.0     # game 3 win rate for player A (post-board)
    results:        list = field(default_factory=list)

    def match_wr_a(self) -> float:
        return round(self.a_wins / max(1, self.n_matches) * 100, 1)

    def match_wr_band_a(self) -> tuple[float, float]:
        """95% Wilson bounds on A's match win rate, as 0-100 pcts.

        Display/serialization only -- do not use in decision logic."""
        from engine.stats_util import wilson_bounds
        lo, hi = wilson_bounds(self.a_wins, self.n_matches)
        return (round(lo * 100, 1), round(hi * 100, 1))

    def play_draw_split(self) -> dict:
        play_w = sum(1 for r in self.results if r.winner == 'a' and r._a_on_play_g1)
        play_n = sum(1 for r in self.results if r._a_on_play_g1)
        draw_w = sum(1 for r in self.results if r.winner == 'a' and not r._a_on_play_g1)
        draw_n = sum(1 for r in self.results if not r._a_on_play_g1)
        return {
            'on_play': round(play_w / max(1, play_n) * 100, 1),
            'on_draw': round(draw_w / max(1, draw_n) * 100, 1),
        }


def _apply_sb(mainboard: list, sideboard: dict,
              sb_in_raw: list, sb_out_raw: list) -> list:
    """Apply sideboard plan and return modified deck. Returns original if no plan."""
    if not sb_in_raw and not sb_out_raw:
        return mainboard
    try:
        return apply_sideboard_plan(mainboard, sideboard, sb_in_raw, sb_out_raw)
    except Exception:
        return mainboard  # fallback to pre-board if sb fails


def run_bo3(apl_a: MatchAPL, deck_a: list, sb_a: dict,
            apl_b: MatchAPL, deck_b: list, sb_b: dict,
            sb_plan_a: tuple = None,  # (sb_in_raw, sb_out_raw) for A vs B
            sb_plan_b: tuple = None,  # (sb_in_raw, sb_out_raw) for B vs A
            a_on_play_g1: bool = True,
            seed: int = None) -> Bo3MatchResult:
    """
    Run a single Best-of-3 match.
    
    Game 1: pre-board decks, a_on_play_g1 determines who goes first
    Game 2: both players sideboard, loser of G1 is on the play
    Game 3: same sideboarded decks, loser of G2 is on the play
    
    sb_plan_a: (["2 Nihil Spellbomb", "1 Wear // Tear"], ["2 Ragavan", "1 Bolt"])
    sb_plan_b: (["3 Leyline of the Void"], ["2 Slickshot", "1 Dart"])
    """
    rng = random.Random(seed)
    result = Bo3MatchResult()
    result._a_on_play_g1 = a_on_play_g1
    
    # Build sideboarded decks
    if sb_plan_a:
        deck_a_sb = _apply_sb(deck_a, sb_a, sb_plan_a[0], sb_plan_a[1])
    else:
        deck_a_sb = deck_a  # no sideboard plan = same deck
    
    if sb_plan_b:
        deck_b_sb = _apply_sb(deck_b, sb_b, sb_plan_b[0], sb_plan_b[1])
    else:
        deck_b_sb = deck_b
    
    # ── GAME 1: pre-board ──
    g1 = run_match(apl_a, deck_a, apl_b, deck_b,
                   on_play=a_on_play_g1, seed=rng.randint(0, 999_999))
    result.game_results.append(g1)
    result.total_turns += g1.turn_count
    
    if g1.winner == 'a':
        result.games_won_a += 1
    else:
        result.games_won_b += 1
    
    # ── GAME 2: post-board, loser on play ──
    a_on_play_g2 = (g1.winner != 'a')  # loser goes first
    g2 = run_match(apl_a, deck_a_sb, apl_b, deck_b_sb,
                   on_play=a_on_play_g2, seed=rng.randint(0, 999_999))
    result.game_results.append(g2)
    result.total_turns += g2.turn_count
    
    if g2.winner == 'a':
        result.games_won_a += 1
    else:
        result.games_won_b += 1
    
    # Check if match is decided (2-0)
    if result.games_won_a == 2:
        result.winner = 'a'
        return result
    if result.games_won_b == 2:
        result.winner = 'b'
        return result
    
    # ── GAME 3: post-board, loser of G2 on play ──
    result.went_to_g3 = True
    a_on_play_g3 = (g2.winner != 'a')
    g3 = run_match(apl_a, deck_a_sb, apl_b, deck_b_sb,
                   on_play=a_on_play_g3, seed=rng.randint(0, 999_999))
    result.game_results.append(g3)
    result.total_turns += g3.turn_count
    
    if g3.winner == 'a':
        result.games_won_a += 1
        result.winner = 'a'
    else:
        result.games_won_b += 1
        result.winner = 'b'
    
    return result


def _run_single_bo3(args):
    """Module-level worker for ProcessPoolExecutor — must be picklable."""
    match_seed, apl_a, deck_a, sb_a, apl_b, deck_b, sb_b, sb_plan_a, sb_plan_b, a_on_play = args
    random.seed(match_seed)
    return run_bo3(apl_a, deck_a, sb_a, apl_b, deck_b, sb_b,
                   sb_plan_a=sb_plan_a, sb_plan_b=sb_plan_b,
                   a_on_play_g1=a_on_play, seed=match_seed)


def run_bo3_set(apl_a: MatchAPL, deck_a: list, sb_a: dict,
                apl_b: MatchAPL, deck_b: list, sb_b: dict,
                sb_plan_a: tuple = None,
                sb_plan_b: tuple = None,
                n: int = 500,
                mix_play_draw: bool = True,
                seed: int = 42,
                n_workers: int = 1) -> Bo3SetResults:
    """
    Run N Bo3 matches. Returns aggregated results.
    mix_play_draw alternates who is on the play in G1.
    n_workers > 1 enables within-matchup parallelism via ProcessPoolExecutor.
    """
    results = Bo3SetResults(n_matches=n)
    rng = random.Random(seed)

    g1_a_wins = 0
    g1_total = 0
    g2_a_wins = 0
    g2_total = 0
    g3_a_wins = 0
    g3_total = 0
    g3_count = 0

    match_seeds  = [rng.randint(0, 999_999) for _ in range(n)]
    match_on_plays = [(i % 2 == 0) if mix_play_draw else True for i in range(n)]

    saved_global_random_state = random.getstate()
    try:
        if n_workers <= 1:
            for i in range(n):
                random.seed(match_seeds[i])
                bo3 = run_bo3(
                    apl_a, deck_a, sb_a,
                    apl_b, deck_b, sb_b,
                    sb_plan_a=sb_plan_a,
                    sb_plan_b=sb_plan_b,
                    a_on_play_g1=match_on_plays[i],
                    seed=match_seeds[i],
                )
                if bo3.winner == 'a':
                    results.a_wins += 1
                else:
                    results.b_wins += 1
                results.results.append(bo3)
                games = bo3.game_results
                if len(games) >= 1:
                    g1_total += 1
                    if games[0].winner == 'a':
                        g1_a_wins += 1
                if len(games) >= 2:
                    g2_total += 1
                    if games[1].winner == 'a':
                        g2_a_wins += 1
                if len(games) >= 3:
                    g3_total += 1
                    g3_count += 1
                    if games[2].winner == 'a':
                        g3_a_wins += 1
        else:
            match_args = [
                (match_seeds[i], apl_a, deck_a, sb_a, apl_b, deck_b, sb_b,
                 sb_plan_a, sb_plan_b, match_on_plays[i])
                for i in range(n)
            ]
            with concurrent.futures.ProcessPoolExecutor(max_workers=n_workers) as pool:
                bo3_results = list(pool.map(_run_single_bo3, match_args))
            for bo3 in bo3_results:
                if bo3.winner == 'a':
                    results.a_wins += 1
                else:
                    results.b_wins += 1
                results.results.append(bo3)
                games = bo3.game_results
                if len(games) >= 1:
                    g1_total += 1
                    if games[0].winner == 'a':
                        g1_a_wins += 1
                if len(games) >= 2:
                    g2_total += 1
                    if games[1].winner == 'a':
                        g2_a_wins += 1
                if len(games) >= 3:
                    g3_total += 1
                    g3_count += 1
                    if games[2].winner == 'a':
                        g3_a_wins += 1
    finally:
        random.setstate(saved_global_random_state)

    results.g1_wr_a = round(g1_a_wins / max(1, g1_total) * 100, 1)
    results.g2_wr_a = round(g2_a_wins / max(1, g2_total) * 100, 1)
    results.g3_wr_a = round(g3_a_wins / max(1, g3_total) * 100, 1) if g3_total else 0
    results.g3_rate = round(g3_count / max(1, n) * 100, 1)
    results.avg_total_turns = round(
        sum(r.total_turns for r in results.results) / max(1, n), 1)
    
    return results


def print_bo3_report(results: Bo3SetResults,
                     name_a: str = "Deck A", name_b: str = "Deck B"):
    """Print formatted Bo3 match report."""
    print(f"\n{'='*55}")
    print(f"  Bo3 MATCHUP: {name_a} vs {name_b}")
    print(f"  {results.n_matches} matches")
    print(f"{'='*55}")
    wr_lo, wr_hi = results.match_wr_band_a()
    print(f"  {name_a} MATCH win rate: {results.match_wr_a()}% [{wr_lo:.1f}–{wr_hi:.1f}]"
          f" ({results.a_wins}-{results.b_wins})")
    pd = results.play_draw_split()
    print(f"  On play: {pd['on_play']}% | On draw: {pd['on_draw']}%")
    print(f"\n  Per-game breakdown:")
    print(f"    G1 (pre-board):  {results.g1_wr_a}%")
    print(f"    G2 (post-board): {results.g2_wr_a}%")
    if results.g3_wr_a:
        print(f"    G3 (post-board): {results.g3_wr_a}%")
    print(f"    Went to G3:      {results.g3_rate}%")
    print(f"    Avg match length: {results.avg_total_turns} turns")
    print()
