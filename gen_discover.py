"""
gen_discover.py -- Evolve a population, mine notations, propose archetypes, synth meta.

Mirrors sim.py conventions. Runs the full discovery loop:
  1. seed a population from every core package (+ auto supports)
  2. evolve() -> records strong card-pair notations
  3. mine_packages() -> promote co-occurring clusters into new packages
  4. propose_archetypes() -> novel core+support combos as fresh seeds
  5. synthesize_meta() -> candidate metagame report

Examples:
  python gen_discover.py --generations 5 --pop 10 --n 1500
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gen.card_pool import CardPool
from gen.package_schema import load_all_packages
from gen.generator import assemble, auto_supports
from gen.deck_writer import write_candidate
from gen.search import evolve
from gen.fitness import evaluate
from gen.notation import NotationStore
from gen.discovery import mine_packages, propose_archetypes
from gen.meta_synth import synthesize_meta
from gen.lineage import Lineage, update_leaderboard


def main():
    ap = argparse.ArgumentParser(description="Discover archetypes via evolution")
    ap.add_argument("--generations", type=int, default=4)
    ap.add_argument("--pop", type=int, default=8)
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--format", default="modern")
    ap.add_argument("--run-id", default="disc")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    import random
    rng = random.Random(args.seed)
    packages = load_all_packages()
    pool = CardPool.load_or_build(args.format)

    cores = [pid for pid, p in packages.items() if p.role in ("combo-core", "aggro-core")]
    seeds = [assemble(c, auto_supports(c, packages), pool, packages) for c in cores]
    seen_sets = {frozenset(s.packages) for s in seeds}

    def eval_fn(cand):
        return evaluate(cand, packages=packages, fmt=args.format, n_goldfish=args.n)

    store = NotationStore.load()
    lin = Lineage(args.run_id)
    print(f"Evolving {len(seeds)} seeds for {args.generations} generations (pop={args.pop})...")
    best, report, store = evolve(seeds, pool, packages, eval_fn,
                                 generations=args.generations, pop_size=args.pop,
                                 rng=rng, notation_store=store, lineage=lin)
    store.save()

    print("\nTop notations (strong card combinations):")
    for nt in store.top(10):
        print(f"  {nt.strength:6.2f}  {' + '.join(nt.cards)}")

    mined = mine_packages(store, pool, run_id=args.run_id)
    print(f"\nMined {len(mined)} candidate package(s) for human review:")
    for pkg in mined:
        print(f"  {pkg.id}: {sorted(pkg.cards)}")

    proposals = propose_archetypes(packages, pool, notation_store=store,
                                   seen_sets=seen_sets, max_proposals=6)
    print(f"\nProposed {len(proposals)} novel archetype(s):")
    entries = []
    for cand in proposals:
        out = write_candidate(cand, fmt=args.format, pool=pool)
        rep = eval_fn(cand)
        entries.append({"deck_id": out["deck_id"], "fitness": rep.fitness,
                        "verdict": rep.verdict, "fidelity": rep.fidelity,
                        "color_identity": cand.color_identity, "packages": cand.packages,
                        "kill_distribution": rep.goldfish.get("kill_distribution", {})})
        print(f"  {cand.name}: fit={rep.fitness} verdict={rep.verdict}")

    if entries:
        update_leaderboard(entries)
        meta = synthesize_meta(entries, run_id=args.run_id)
        print(f"\nSynthesized candidate metagame -> {meta.get('_path')}")
        for f in meta["field"]:
            print(f"  {f['share_pct']:5.1f}%  {f['deck_id']}  (intra-field WR {f['intra_field_wr']}%)")


if __name__ == "__main__":
    main()
