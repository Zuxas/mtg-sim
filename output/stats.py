"""
stats.py — Stat visualization and reporting

Wraps SimulationResults with matplotlib charts and JSON export.
Histogram approach adapted from wujason9/Monte-Carlo-Analysis-Toolkit (MIT).

Usage:
    from output.stats import plot_kill_curve, save_report
    plot_kill_curve(results)
    save_report(results, "reports/humans_10k.json")
"""

import json
import os
from datetime import datetime
from typing import Optional

try:
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def plot_kill_curve(results, save_path: Optional[str] = None, show: bool = True):
    """
    Bar chart of kill turn distribution.
    X = turn number, Y = % of all games won that turn.
    """
    if not HAS_MPL:
        print("  matplotlib not installed — run: pip install matplotlib")
        return

    dist = results.kill_turn_distribution()
    if not dist:
        print("  No wins to plot.")
        return

    turns = sorted(dist.keys())
    pcts  = [dist[t] for t in turns]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(turns, pcts, color="#1d5fa8", edgecolor="#0d3f78", linewidth=0.5)

    # Annotate each bar
    for bar, pct in zip(bars, pcts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"{pct:.1f}%",
            ha="center", va="bottom", fontsize=9, color="#333"
        )

    # Cumulative line
    cumulative = []
    running = 0.0
    for t in turns:
        running += dist[t]
        cumulative.append(running)

    ax2 = ax.twinx()
    ax2.plot(turns, cumulative, color="#e05c2a", marker="o", linewidth=1.5,
             markersize=4, label="Cumulative %")
    ax2.set_ylabel("Cumulative win %", color="#e05c2a", fontsize=10)
    ax2.tick_params(axis="y", labelcolor="#e05c2a")
    ax2.set_ylim(0, 105)

    ax.set_xlabel("Turn", fontsize=11)
    ax.set_ylabel("% of games won this turn", fontsize=11)
    ax.set_title(
        f"{results.archetype}  |  {results.n_games:,} games  |  "
        f"Win rate {results.win_rate()*100:.1f}%  |  Avg kill T{results.avg_kill_turn():.2f}",
        fontsize=12, pad=12
    )
    ax.set_xticks(turns)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.set_ylim(0, max(pcts) * 1.25)

    fig.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, dpi=150)
        print(f"  Chart saved: {save_path}")

    if show:
        plt.show()

    plt.close(fig)


def print_summary(results):
    """Print a formatted summary table to stdout."""
    print(results.summary())

    # Cumulative breakdown
    print("  Cumulative win % by turn:")
    cumulative = 0.0
    for turn, pct in sorted(results.kill_turn_distribution().items()):
        cumulative += pct
        print(f"    By T{turn:2d}: {cumulative:5.1f}%")
    print()


def save_report(results, path: str):
    """Save full results as JSON for later analysis or Claude API input."""
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    data = results.to_dict()
    data["generated_at"] = datetime.now().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"  Report saved: {path}")
    return data


def compare_results(results_list: list, labels: Optional[list[str]] = None,
                    save_path: Optional[str] = None, show: bool = True):
    """
    Side-by-side bar chart comparing multiple sim runs.
    Useful for comparing deck variants (e.g. 3x vs 4x Militia Bugler).
    """
    if not HAS_MPL:
        print("  matplotlib not installed")
        return

    import numpy as np

    labels = labels or [r.archetype for r in results_list]
    all_turns = sorted(set(
        t for r in results_list for t in r.kill_turn_distribution()
    ))

    x = np.arange(len(all_turns))
    width = 0.8 / len(results_list)
    colors = ["#1d5fa8", "#e05c2a", "#2a8a3e", "#9b2a9b", "#c4a000"]

    fig, ax = plt.subplots(figsize=(11, 5))

    for i, (result, label) in enumerate(zip(results_list, labels)):
        dist = result.kill_turn_distribution()
        pcts = [dist.get(t, 0) for t in all_turns]
        offset = (i - len(results_list) / 2 + 0.5) * width
        ax.bar(x + offset, pcts, width, label=label,
               color=colors[i % len(colors)], edgecolor="white", linewidth=0.4)

    ax.set_xlabel("Turn")
    ax.set_ylabel("% of games won this turn")
    ax.set_title("Kill Turn Distribution — Variant Comparison")
    ax.set_xticks(x)
    ax.set_xticklabels([f"T{t}" for t in all_turns])
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.legend()
    fig.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, dpi=150)
        print(f"  Comparison chart saved: {save_path}")

    if show:
        plt.show()

    plt.close(fig)
