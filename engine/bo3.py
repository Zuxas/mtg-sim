"""
engine/bo3.py — Best-of-3 match simulation

Models a full Bo3 match:
  - Game 1: both players on pre-board decks
  - Games 2-3: player who lost the previous game sideboards
  - Accounts for play/draw alternation

Bo3 match win formula:
  P(match win) = P(G1) * P(G2|on_draw)
               + P(G1) * P(G2|fail) * P(G3)
               + P(G1|fail) * P(G2|on_play) * P(G3)

Where "on_draw" in G2 = we won G1 (opponent plays G2), etc.

Usage:
    from engine.bo3 import simulate_bo3_match, simulate_bo3_gauntlet

    result = simulate_bo3_match(
        our_apl        = HumansAPL(),
        our_mainboard  = main,
        our_sideboard  = side,
        opp_archetype  = "Elves",
        opp_clock_dist = ARCHETYPE_CLOCKS["elves"],
        n_games        = 3000,
    )
    print(result.match_win_pct)  # e.g. 62.4
"""

import random
from dataclasses import dataclass, field
from typing import Optional

from engine.runner import run_simulation


@dataclass
class Bo3Result:
    deck_name:       str
    opponent:        str

    # Game win rates
    g1_win_pct:      float = 0.0   # pre-board, on play
    g2_win_pct:      float = 0.0   # post-board, on draw (lost G1 scenario)
    g3_win_pct:      float = 0.0   # post-board, 50/50

    # Match win rate (computed)
    match_win_pct:   float = 0.0

    # Kill turns
    g1_avg_kill:     float = 0.0
    g2_avg_kill:     float = 0.0

    # Sample sizes
    n_g1:            int = 0
    n_g2:            int = 0

    def summary(self) -> str:
        return (f"{self.deck_name} vs {self.opponent}: "
                f"G1={self.g1_win_pct:.1f}% G2={self.g2_win_pct:.1f}% "
                f"Match={self.match_win_pct:.1f}%")


def compute_match_win_pct(g1: float, g2_on_draw: float, g2_on_play: float,
                          g3: float) -> float:
    """
    Compute Bo3 match win% from game win percentages.
    All inputs are 0-100 floats.

    Scenarios we win the match:
      W-W: win G1 AND win G2 (on draw)
      W-L-W: win G1, lose G2, win G3
      L-W-W: lose G1, win G2 (on play), win G3
    """
    p1 = g1 / 100
    p2d = g2_on_draw / 100   # our G2 win rate when on the draw
    p2p = g2_on_play / 100   # our G2 win rate when on the play
    p3  = g3 / 100

    match_win = (
        p1 * p2d                    # W-W
        + p1 * (1 - p2d) * p3      # W-L-W
        + (1 - p1) * p2p * p3      # L-W-W
    )
    return round(match_win * 100, 1)


def simulate_bo3_match(
    our_apl,
    our_mainboard:  list,
    our_sideboard:  dict,           # {card_name: qty}
    opp_archetype:  str,
    opp_clock_dist: dict,           # {turn: pct} kill distribution
    n_games:        int   = 2000,
    our_deck_name:  str   = "",
    playbooks:      dict  = None,
    real_matchup_matrix: dict = None,  # from MetaBridge
) -> Bo3Result:
    """
    Simulate a Bo3 match.

    G1: goldfish race with pre-board decks
    G2: post-board on the draw (we lost G1) vs adjusted opponent clock
    G3: post-board 50/50 play/draw
    """
    from engine.sideboard import get_sb_plan, apply_sideboard_plan
    from sim_bridge import race_win_pct, avg_kill_turn

    result = Bo3Result(
        deck_name=our_deck_name or (our_apl.name if our_apl else "Unknown"),
        opponent=opp_archetype,
        n_g1=n_games,
        n_g2=n_games,
    )

    # ── G1: pre-board ────────────────────────────────────────────────────
    # Try real matchup data first
    if real_matchup_matrix:
        key = (result.deck_name, opp_archetype)
        for (a, b), wp in real_matchup_matrix.items():
            if opp_archetype.lower() in b.lower() and result.deck_name.lower() in a.lower():
                result.g1_win_pct = wp
                break

    if not result.g1_win_pct:
        # Simulate goldfish race
        sim = run_simulation(our_apl, our_mainboard, n=n_games, on_play=True, seed=42)
        our_dist = sim.kill_turn_distribution()
        result.g1_win_pct = race_win_pct(our_dist, opp_clock_dist, n=50000)
        result.g1_avg_kill = avg_kill_turn(our_dist)

    # ── Build post-board deck ─────────────────────────────────────────────
    sb_in_raw, sb_out_raw = get_sb_plan(
        result.deck_name, opp_archetype, playbooks
    )

    if sb_in_raw or sb_out_raw:
        post_board_deck = apply_sideboard_plan(
            our_mainboard, our_sideboard, sb_in_raw, sb_out_raw
        )
    else:
        post_board_deck = our_mainboard  # no sb plan found — use pre-board

    # ── G2: post-board on the draw ────────────────────────────────────────
    sim2 = run_simulation(our_apl, post_board_deck, n=n_games, on_play=False, seed=43)
    our_dist2 = sim2.kill_turn_distribution()

    # Opponent also sideboards — assume their clock improves by ~5% (hate cards cost tempo)
    opp_dist2 = _adjust_opp_clock(opp_clock_dist, hate_factor=0.05)

    result.g2_win_pct  = race_win_pct(our_dist2, opp_dist2, n=50000)
    result.g2_avg_kill = avg_kill_turn(our_dist2)

    # G2 on the play (for L-W-W scenario)
    sim2p = run_simulation(our_apl, post_board_deck, n=n_games, on_play=True, seed=44)
    our_dist2p = sim2p.kill_turn_distribution()
    g2_on_play = race_win_pct(our_dist2p, opp_dist2, n=50000)

    # G3: 50/50 play/draw post-board
    g3 = (result.g2_win_pct + g2_on_play) / 2

    result.g3_win_pct = g3
    result.match_win_pct = compute_match_win_pct(
        result.g1_win_pct,
        result.g2_win_pct,  # on draw
        g2_on_play,          # on play
        g3,
    )

    return result


def _adjust_opp_clock(dist: dict, hate_factor: float = 0.05) -> dict:
    """
    Shift opponent's kill distribution slightly slower post-board.
    hate_factor=0.05 means 5% of their kills shift one turn later.
    Models the tempo cost of bringing in hate cards.
    """
    if not dist:
        return dist
    adjusted = dict(dist)
    turns = sorted(dist.keys())
    for t in turns[:-1]:
        shift = dist[t] * hate_factor
        adjusted[t]   = adjusted.get(t, 0) - shift
        adjusted[t+1] = adjusted.get(t+1, 0) + shift
    return {k: max(0, v) for k, v in adjusted.items()}


# ---------------------------------------------------------------------------
# Gauntlet: run Bo3 against entire field
# ---------------------------------------------------------------------------

@dataclass
class Bo3GauntletResult:
    our_deck:   str
    format_name: str
    matchups:   list[Bo3Result]   = field(default_factory=list)
    avg_match_win: float          = 0.0

    def summary_table(self) -> str:
        lines = [f"Bo3 Gauntlet — {self.our_deck} ({self.format_name})\n"]
        lines.append(f"  {'Opponent':<28} {'G1':>6} {'G2':>6} {'Match':>7}")
        lines.append("  " + "-" * 52)
        for r in sorted(self.matchups, key=lambda x: -x.match_win_pct):
            lines.append(f"  {r.opponent:<28} {r.g1_win_pct:>5.1f}% {r.g2_win_pct:>5.1f}% "
                         f"{r.match_win_pct:>6.1f}%")
        lines.append("  " + "-" * 52)
        lines.append(f"  {'AVERAGE':<28} {'':>6} {'':>6} {self.avg_match_win:>6.1f}%")
        return "\n".join(lines)


def simulate_bo3_gauntlet(
    our_deck_name:  str,
    our_apl,
    our_mainboard:  list,
    our_sideboard:  dict,
    field:          dict,     # {archetype: field_share}
    opp_clocks:     dict,     # {archetype: kill_distribution}
    n_games:        int = 1000,
    format_name:    str = "legacy",
    playbooks:      dict = None,
    real_matchup_matrix: dict = None,
) -> Bo3GauntletResult:
    """Run Bo3 against every deck in the field."""
    gauntlet = Bo3GauntletResult(our_deck=our_deck_name, format_name=format_name)

    for opp_arch, share in field.items():
        if opp_arch == our_deck_name:
            continue

        opp_dist = opp_clocks.get(opp_arch, opp_clocks.get("unknown", {5: 100.0}))
        print(f"  vs {opp_arch} ({share*100:.1f}%)...")

        r = simulate_bo3_match(
            our_apl=our_apl,
            our_mainboard=our_mainboard,
            our_sideboard=our_sideboard,
            opp_archetype=opp_arch,
            opp_clock_dist=opp_dist,
            n_games=n_games,
            our_deck_name=our_deck_name,
            playbooks=playbooks,
            real_matchup_matrix=real_matchup_matrix,
        )
        gauntlet.matchups.append(r)

    if gauntlet.matchups:
        # Weight by field share
        total_share = sum(field.get(r.opponent, 1) for r in gauntlet.matchups)
        gauntlet.avg_match_win = round(
            sum(r.match_win_pct * field.get(r.opponent, 1)
                for r in gauntlet.matchups) / total_share,
            1
        )

    return gauntlet
