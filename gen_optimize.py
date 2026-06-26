"""
gen_optimize.py -- Hill-climb a seed deck on simulated fitness.

Mirrors sim.py conventions. Builds a seed from packages (or auto supports),
then improves it with gen.search.hill_climb scored by gen.fitness.evaluate
(which auto-generates a cached APL and goldfishes the deck).

Examples:
  python gen_optimize.py --core boros_energy_core --auto --rounds 20 --n 2000
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gen.card_pool import CardPool
from gen.package_schema import load_all_packages
from gen.generator import assemble, auto_supports
from gen.deck_writer import write_candidate
from gen.search import hill_climb
from gen.fitness import evaluate
from gen.lineage import Lineage, update_leaderboard


def main():
    ap = argparse.ArgumentParser(description="Optimize a deck via hill climbing")
    ap.add_argument("--core", required=True)
    ap.add_argument("--supports", default="")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--rounds", type=int, default=20)
    ap.add_argument("--n", type=int, default=2000, help="goldfish games per evaluation")
    ap.add_argument("--format", default="modern")
    ap.add_argument("--run-id", default="opt")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    packages = load_all_packages()
    pool = CardPool.load_or_build(args.format)
    supports = (auto_supports(args.core, packages) if args.auto
                else [s for s in args.supports.split(",") if s])
    seed = assemble(args.core, supports, pool, packages)

    def eval_fn(cand):
        return evaluate(cand, packages=packages, fmt=args.format, n_goldfish=args.n)

    import random
    lin = Lineage(args.run_id)
    print(f"Optimizing {seed.name} for {args.rounds} rounds (n={args.n})...")

    def on_step(r, op, fit, best, improved):
        flag = "+" if improved else " "
        print(f"  [{r:3d}] {op:18s} fit={fit:6.2f} best={best:6.2f} {flag}")

    best, report = hill_climb(seed, pool, packages, eval_fn, rounds=args.rounds,
                              rng=random.Random(args.seed), lineage=lin, on_step=on_step)

    out = write_candidate(best, fmt=args.format, pool=pool)
    update_leaderboard([{
        "deck_id": out["deck_id"], "fitness": report.fitness, "verdict": report.verdict,
        "fidelity": report.fidelity, "field_wr": report.field_wr,
        "color_identity": best.color_identity, "packages": best.packages,
    }])

    print(f"\nBest: {best.name}")
    print(f"  Fitness  : {report.fitness}  Verdict: {report.verdict}  Fidelity: {report.fidelity}")
    print(f"  Field WR : {report.field_wr}%")
    print(f"  Deck file: {out['deck_file']}")
    print(f"  Lineage  : {lin.dir}")


if __name__ == "__main__":
    main()
