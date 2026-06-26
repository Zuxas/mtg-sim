"""
gen/smoke.py -- End-to-end smoke test of the generation pipeline.

Generates and scores a few Modern decks from the seed packages against the REAL
oracle DB. Requires data/rules_reference/scryfall_oracle_cards.json (fetch via
scripts/fetch_scryfall_bulk.sh) and, for APL generation, Claude Code creds.

Skips cleanly (exit 0) when the oracle DB is absent, so it is safe to run in a
data-less container; it does real work in a populated environment.

Run: python gen/smoke.py [--n 500]
"""

import os
import sys
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gen.card_pool import CardPool, ORACLE_PATH
from gen.package_schema import load_all_packages
from gen.generator import assemble, auto_supports
from gen.deck_writer import write_candidate


def main():
    ap = argparse.ArgumentParser(description="Pipeline smoke test")
    ap.add_argument("--n", type=int, default=500, help="goldfish games per deck")
    ap.add_argument("--format", default="modern")
    ap.add_argument("--no-sim", action="store_true",
                    help="generate + write only; skip APL generation and sims")
    args = ap.parse_args()

    if not os.path.exists(ORACLE_PATH):
        print("SKIP: oracle DB not present "
              "(run scripts/fetch_scryfall_bulk.sh to enable the smoke test).")
        return 0

    packages = load_all_packages()
    pool = CardPool.load_or_build(args.format)
    print(f"Pool: {len(pool)} legal cards, {len(pool.simulatable_names())} simulatable")

    cores = [pid for pid, p in packages.items()
             if p.role in ("combo-core", "aggro-core")][:3]
    failures = []
    for core in cores:
        supports = auto_supports(core, packages)
        cand = assemble(core, supports, pool, packages, validate_mana=True)
        out = write_candidate(cand, fmt=args.format, pool=pool)
        ok60 = cand.main_count() == 60
        print(f"\n[{core}] -> {out['deck_id']}  main={cand.main_count()} "
              f"fidelity={cand.metadata.get('fidelity')} "
              f"castability={cand.metadata.get('castability')}")
        if not ok60:
            failures.append(f"{core}: mainboard {cand.main_count()} != 60")

        if args.no_sim:
            continue
        try:
            from gen.fitness import evaluate
            t0 = time.perf_counter()
            rep = evaluate(cand, packages=packages, fmt=args.format, n_goldfish=args.n)
            dt = time.perf_counter() - t0
            print(f"    fitness={rep.fitness} verdict={rep.verdict} "
                  f"field_wr={rep.field_wr}% apl={rep.apl_source} ({dt:.1f}s)")
        except Exception as e:
            print(f"    sim/eval skipped: {e}")

    print()
    if failures:
        print("SMOKE FAILED:")
        for f in failures:
            print(f"  {f}")
        return 1
    print("Smoke generation OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
