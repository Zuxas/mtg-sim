"""
sim.py — Main entry point for MTG Sim

Usage:
    python sim.py                          # run Humans, 10k games, show chart + analysis
    python sim.py --n 50000               # more iterations
    python sim.py --deck decks/humans_legacy.txt
    python sim.py --no-chart              # skip matplotlib
    python sim.py --no-claude             # skip API analysis
    python sim.py --draw                  # simulate on the draw
    python sim.py --question "Is this fast enough to race Lands game 1?"
"""

import sys
import os
import argparse

# --- Path setup ---
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mtg-meta-analyzer"))

from data.deck import load_deck_from_file
from apl.humans import HumansAPL
from engine.runner import run_simulation
from output.stats import print_summary, plot_kill_curve, save_report
from output.claude_analysis import analyze
from engine.race import field_report
from engine.opponent import LEGACY_FIELD


def main():
    parser = argparse.ArgumentParser(description="MTG Goldfish Simulator")
    parser.add_argument("--deck",      default="decks/humans_legacy.txt")
    parser.add_argument("--n",         type=int, default=10_000)
    parser.add_argument("--draw",      action="store_true")
    parser.add_argument("--no-chart",  action="store_true")
    parser.add_argument("--no-claude", action="store_true")
    parser.add_argument("--context",   default="Legacy locals: Lands, Delver, Elves, Painter, Stoneforge, Hogaak")
    parser.add_argument("--question",  default=None)
    parser.add_argument("--save",      default=None, help="Save JSON report to path")
    parser.add_argument("--seed",      type=int, default=None)
    args = parser.parse_args()

    deck_path = os.path.join(os.path.dirname(__file__), args.deck)

    print(f"\nLoading deck: {args.deck}")
    main_deck, _ = load_deck_from_file(deck_path)

    print(f"\nRunning {args.n:,} simulations ({'draw' if args.draw else 'play'})...\n")
    results = run_simulation(
        apl=HumansAPL(),
        mainboard=main_deck,
        n=args.n,
        on_play=not args.draw,
        verbose_first=1,
        seed=args.seed,
    )

    print_summary(results)

    print(field_report(results, LEGACY_FIELD))

    if args.save:
        save_report(results, args.save)

    if not args.no_chart:
        chart_path = f"reports/kill_curve_{results.archetype.replace(' ', '_').lower()}.png"
        plot_kill_curve(results, save_path=chart_path, show=True)

    if not args.no_claude:
        print("\n── Claude Analysis ──────────────────────────────────────")
        try:
            analysis = analyze(
                results,
                context=args.context,
                question=args.question,
            )
            print(analysis)
        except EnvironmentError as e:
            print(f"  Skipped: {e}")
        except Exception as e:
            print(f"  API error: {e}")
        print("─────────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
