"""
runner.py — Monte Carlo simulation runner

Runs N goldfish games for a given deck + APL and returns aggregated stats.

Usage:
    from engine.runner import run_simulation
    from apl.humans import HumansAPL
    from data.deck import load_deck_from_file

    main, side = load_deck_from_file("decks/humans.txt")
    results = run_simulation(HumansAPL(), main, n=10000)
    print(results.summary())
"""

import time
import statistics
from dataclasses import dataclass, field
from typing import Optional

from data.card import Card
from engine.game_state import GameResult
from apl.base_apl import BaseAPL


# ---------------------------------------------------------------------------
# SimulationResults — aggregated output of N games
# ---------------------------------------------------------------------------

@dataclass
class SimulationResults:
    archetype:      str
    n_games:        int
    on_play_split:  float   # fraction of games run on the play

    kill_turns:     list[int]   = field(default_factory=list)
    mulligans:      list[int]   = field(default_factory=list)
    won_games:      int         = 0
    elapsed_sec:    float       = 0.0

    # Per-game results (optional, for detailed analysis)
    game_logs:      list[GameResult] = field(default_factory=list)

    # -----------------------------------------------------------------------
    # Computed stats
    # -----------------------------------------------------------------------

    def win_rate(self) -> float:
        return self.won_games / self.n_games if self.n_games else 0

    def avg_kill_turn(self) -> Optional[float]:
        return statistics.mean(self.kill_turns) if self.kill_turns else None

    def median_kill_turn(self) -> Optional[float]:
        return statistics.median(self.kill_turns) if self.kill_turns else None

    def kill_turn_distribution(self) -> dict[int, float]:
        """% of games won on each turn."""
        dist: dict[int, int] = {}
        for t in self.kill_turns:
            dist[t] = dist.get(t, 0) + 1
        return {t: round(c / self.n_games * 100, 1) for t, c in sorted(dist.items())}

    def win_by_turn(self, turn: int) -> float:
        """% of all games won by (and including) turn N."""
        if not self.kill_turns:
            return 0.0
        return round(sum(1 for t in self.kill_turns if t <= turn) / self.n_games * 100, 1)

    def avg_mulligans(self) -> float:
        return statistics.mean(self.mulligans) if self.mulligans else 0

    def mull_rate(self) -> float:
        """% of games that took at least 1 mulligan."""
        return round(sum(1 for m in self.mulligans if m > 0) / len(self.mulligans) * 100, 1) if self.mulligans else 0

    # -----------------------------------------------------------------------
    # Human-readable output
    # -----------------------------------------------------------------------

    def summary(self) -> str:
        lines = [
            f"",
            f"  == {self.archetype} | {self.n_games:,} games ==",
            f"  Win rate       : {self.win_rate()*100:.1f}%",
            f"  Avg kill turn  : {self.avg_kill_turn():.2f}" if self.avg_kill_turn() else "  Avg kill turn  : N/A",
            f"  Median kill    : {self.median_kill_turn():.0f}" if self.median_kill_turn() else "  Median kill    : N/A",
            f"  Win by T3      : {self.win_by_turn(3)}%",
            f"  Win by T4      : {self.win_by_turn(4)}%",
            f"  Win by T5      : {self.win_by_turn(5)}%",
            f"  Avg mulligans  : {self.avg_mulligans():.2f}  ({self.mull_rate()}% mulled)",
            f"  Runtime        : {self.elapsed_sec:.2f}s ({self.n_games/self.elapsed_sec:.0f} games/sec)" if self.elapsed_sec else "",
            f"",
            f"  Kill turn breakdown:",
        ]
        for turn, pct in self.kill_turn_distribution().items():
            bar = "█" * int(pct / 2)
            lines.append(f"    T{turn:2d}  {pct:5.1f}%  {bar}")
        lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "archetype":        self.archetype,
            "n_games":          self.n_games,
            "win_rate":         round(self.win_rate(), 4),
            "avg_kill_turn":    self.avg_kill_turn(),
            "median_kill_turn": self.median_kill_turn(),
            "win_by_t3":        self.win_by_turn(3),
            "win_by_t4":        self.win_by_turn(4),
            "win_by_t5":        self.win_by_turn(5),
            "avg_mulligans":    round(self.avg_mulligans(), 3),
            "mull_rate":        self.mull_rate(),
            "kill_distribution": self.kill_turn_distribution(),
            "elapsed_sec":      round(self.elapsed_sec, 3),
        }


# ---------------------------------------------------------------------------
# Main simulation entry point
# ---------------------------------------------------------------------------

def run_simulation(
    apl: BaseAPL,
    mainboard: list[Card],
    n: int = 10_000,
    on_play: bool = True,
    mixed_play_draw: bool = False,
    store_logs: bool = False,
    save_logs:  bool = False,   # alias for store_logs (ML data collection)
    verbose_first: int = 0,
    seed: Optional[int] = None,
) -> SimulationResults:
    """
    Run N goldfish games and return aggregated SimulationResults.

    Args:
        apl:            Archetype APL instance
        mainboard:      60-card deck as list of Card objects
        n:              Number of games to simulate
        on_play:        Whether to always be on the play (overridden by mixed_play_draw)
        mixed_play_draw: Randomly alternate on_play/on_draw 50/50
        store_logs:     Store individual GameResult objects (memory intensive)
        verbose_first:  Print full turn log for first N games (debugging)
        seed:           Random seed for reproducibility
    """
    results = SimulationResults(
        archetype=apl.name,
        n_games=n,
        on_play_split=0.5 if mixed_play_draw else (1.0 if on_play else 0.0),
    )

    import random
    import copy
    if seed is not None:
        random.seed(seed)

    start = time.perf_counter()

    def _fresh_deck(deck):
        """Create a clean deck copy with independent objects and reset state.
        Uses shallow copy + tag clone (8.7x faster than deepcopy, same correctness)."""
        fresh = []
        for c in deck:
            nc = copy.copy(c)
            nc.tags = set(c.tags)  # independent tag set
            nc.tapped = False
            nc.summoning_sickness = False
            nc.turn_entered = 0
            nc.counters = 0
            fresh.append(nc)
        return fresh

    for i in range(n):
        # CRITICAL: Each game needs a fresh deck with independent Card objects.
        # Without this, mutations from game N (tapped, turn_entered, tags)
        # persist into game N+1. By game 100, most cards have stale state.
        game_deck = _fresh_deck(mainboard)
        # Reset event bus each game so opponent model starts fresh
        from engine.game_events import reset_event_bus
        reset_event_bus()
        # Re-subscribe if APL has an opponent model
        if hasattr(apl, 'opp_model') and apl.opp_model is not None:
            from engine.opponent_model import OpponentHandModel
            apl.set_opponent(apl.opp_model.archetype_key, apl.opp_model.on_play)

        game_on_play = on_play
        if mixed_play_draw:
            game_on_play = random.random() < 0.5

        verbose = i < verbose_first
        game_result = apl.run_game(
            mainboard=game_deck,
            on_play=game_on_play,
            verbose=verbose,
        )

        results.mulligans.append(game_result.mulligans)

        if game_result.won:
            results.won_games += 1
            results.kill_turns.append(game_result.kill_turn)

        if store_logs or save_logs:
            results.game_logs.append(game_result)

        # Progress indicator — only show if verbose or n >= 10000
        if verbose and n >= 1000 and (i + 1) % (n // 10) == 0:
            pct = (i + 1) / n * 100
            print(f"  {pct:.0f}%  ({i+1:,}/{n:,} games, "
                  f"{results.won_games/(i+1)*100:.1f}% win rate so far)")

    results.elapsed_sec = time.perf_counter() - start
    return results


# ---------------------------------------------------------------------------
# CLI — run a quick sim from the command line
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from data.deck import load_deck_from_text
    from apl.humans import HumansAPL

    # Minimal Humans shell for testing (real list goes in decks/)
    sample_list = """
4 Champion of the Parish
4 Thalia's Lieutenant
4 Mantis Rider
4 Reflector Mage
4 Militia Bugler
3 Thalia, Guardian of Thraben
3 Aether Vial
4 Cavern of Souls
4 Unclaimed Territory
4 Horizon Canopy
4 Ancient Ziggurat
3 Seachrome Coast
2 Plains
1 Island
2 Kitesail Freebooter
4 Phantasmal Image
4 Meddling Mage
2 Imperial Recruiter
""".strip()

    print("Loading deck...")
    main, _ = load_deck_from_text(sample_list)
    print(f"  {len(main)} cards loaded\n")

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10_000
    print(f"Running {n:,} simulations...")

    results = run_simulation(
        apl=HumansAPL(),
        mainboard=main,
        n=n,
        on_play=True,
        verbose_first=1,   # print the first game's full log
        seed=42,
    )

    print(results.summary())

    from engine.race import field_report
    from engine.opponent import LEGACY_FIELD
    print(field_report(results, LEGACY_FIELD))
