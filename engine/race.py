"""
race.py — Race win probability calculator

Given our SimulationResults and an opponent clock, calculates:
  - P(we kill before they do) — raw goldfish race
  - Expected G1 win rate per matchup
  - Full field summary

Usage:
    from engine.race import race_analysis, field_report
    from engine.opponent import LEGACY_FIELD

    report = field_report(our_results, LEGACY_FIELD)
    print(report)
"""

from engine.opponent import OpponentClock, LEGACY_FIELD
import statistics


def race_win_probability(
    our_kill_distribution: dict[int, float],
    opponent: OpponentClock,
    n_samples: int = 100_000,
) -> dict:
    """
    Monte Carlo race simulation.
    We win if our kill turn <= opponent's kill turn.
    Both distributions are sampled independently.

    Returns dict with win_pct, loss_pct, draw_pct, avg_margin.
    """
    import random

    # Build our CDF for fast sampling
    our_turns = sorted(our_kill_distribution)
    our_cumulative = []
    running = 0.0
    for t in our_turns:
        running += our_kill_distribution[t]
        our_cumulative.append((t, running))

    def sample_us():
        roll = random.random() * 100
        for t, cum in our_cumulative:
            if roll <= cum:
                return t
        return 99  # didn't kill (99 = never in practical terms)

    wins = losses = 0
    margins = []

    for _ in range(n_samples):
        our_turn = sample_us()
        opp_turn = opponent.sample_kill_turn() or 99

        if our_turn <= opp_turn:
            wins += 1
            margins.append(opp_turn - our_turn)
        else:
            losses += 1
            margins.append(our_turn - opp_turn)

    win_pct = wins / n_samples * 100
    loss_pct = losses / n_samples * 100
    avg_margin = statistics.mean(margins)

    return {
        "matchup":      opponent.name,
        "win_pct":      round(win_pct, 1),
        "loss_pct":     round(loss_pct, 1),
        "avg_margin":   round(avg_margin, 2),
        "verdict":      _verdict(win_pct),
    }


def _verdict(win_pct: float) -> str:
    if win_pct >= 65:  return "Favorable"
    if win_pct >= 55:  return "Slightly Favorable"
    if win_pct >= 45:  return "Even"
    if win_pct >= 35:  return "Slightly Unfavorable"
    return "Unfavorable"


def field_report(results, field: dict = None, n_samples: int = 100_000) -> str:
    """
    Run race analysis against every deck in the field.
    Returns a formatted report string.
    """
    field = field or LEGACY_FIELD
    dist  = results.kill_turn_distribution()

    lines = [
        f"",
        f"  == {results.archetype} — G1 Race Analysis vs Field ==",
        f"  Our clock: avg T{results.avg_kill_turn():.1f} | "
        f"median T{results.median_kill_turn():.0f} | "
        f"win rate {results.win_rate()*100:.1f}% (goldfish)",
        f"",
        f"  {'Matchup':<22} {'Our Win%':>8}  {'Verdict':<22} {'Avg margin':>10}",
        f"  {'-'*66}",
    ]

    matchup_results = []
    for name, opp in field.items():
        r = race_win_probability(dist, opp, n_samples)
        matchup_results.append(r)
        verdict_icon = {
            "Favorable":           "+",
            "Slightly Favorable":  "+",
            "Even":                "=",
            "Slightly Unfavorable":"-",
            "Unfavorable":         "-",
        }.get(r["verdict"], "?")
        lines.append(
            f"  {name:<22} {r['win_pct']:>7.1f}%  "
            f"[{verdict_icon}] {r['verdict']:<20} "
            f"{r['avg_margin']:>+.1f} turns"
        )

    avg_field_wr = statistics.mean(r["win_pct"] for r in matchup_results)
    lines += [
        f"  {'-'*66}",
        f"  {'Avg vs field':<22} {avg_field_wr:>7.1f}%",
        f"",
    ]

    return "\n".join(lines)


def print_field_report(results, field: dict = None):
    print(field_report(results, field))
