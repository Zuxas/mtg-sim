"""
tests/test_search.py -- Phase 4 tests for the optimizer (hill-climb + evolve).

Offline: an injected deterministic evaluator scores candidates by a property the
mutation operators can actually move (kill-curve cost), so we can assert the loop
improves and stays legal without the oracle DB.

Run: python tests/test_search.py
"""

import os
import sys
import random
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from engine.mana import parse_cost
from gen.card_pool import CardPool, PoolCard
from gen.package_schema import Package
from gen.generator import assemble
from gen.search import (hill_climb, evolve, mut_swap_card, mut_adjust_count,
                        mut_swap_support, mut_resolve_mana)
from gen.notation import NotationStore
from gen.lineage import Lineage, update_leaderboard
from gen.parallel_eval import evaluate_population

BASICS = {"W": "Plains", "G": "Forest", "R": "Mountain", "U": "Island"}


def _creature(name, color, cmc):
    cost = "{1}{" + color + "}" if cmc == 2 else "{2}{" + color + "}"
    return PoolCard(name=name, cmc=cmc, mana_cost=cost, type_line="Creature - Beast",
                    color_identity=[color], colors=[color], pips=parse_cost(cost),
                    is_land=False, sim_bucket="VANILLA", simulatable=True)


def _land(name, type_line, identity):
    return PoolCard(name=name, cmc=0.0, mana_cost="", type_line=type_line,
                    color_identity=list(identity), colors=[], pips={"generic": 0},
                    is_land=True, sim_bucket="VANILLA", simulatable=True)


def make_pool():
    cards = {b: _land(b, f"Basic Land - {b}", [c]) for c, b in BASICS.items()}
    cards["Temple Garden"] = _land("Temple Garden", "Land - Forest Plains", ["G", "W"])
    for color in ("G", "W"):
        for i in range(1, 13):
            n = f"{color} Vanilla {i}"
            cards[n] = _creature(n, color, cmc=2 if i % 2 else 3)
    return CardPool("modern", cards)


def make_packages():
    core = Package(id="gw_core", name="GW Core", role="aggro-core",
                   cards={"G Vanilla 1": 4, "W Vanilla 1": 4, "G Vanilla 2": 4},
                   color_identity=["G", "W"], conjoins_with=["gw"], tags=["gw"],
                   min_slots=12, max_slots=12)
    eng = Package(id="gw_eng", name="GW Engine", role="engine",
                  cards={"G Vanilla 4": 4}, color_identity=["G", "W"],
                  conjoins_with=[], tags=["gw"], min_slots=4, max_slots=4)
    pay = Package(id="gw_pay", name="GW Payoff", role="payoff",
                  cards={"W Vanilla 6": 4}, color_identity=["G", "W"],
                  conjoins_with=[], tags=["gw"], min_slots=4, max_slots=4)
    return {"gw_core": core, "gw_eng": eng, "gw_pay": pay}


def _avg_cmc(cand, pool):
    tot = qty = 0
    for n, q in cand.mainboard.items():
        pc = pool.get(n)
        if pc and not pc.is_land:
            tot += pc.cmc * q
            qty += q
    return tot / qty if qty else 0


class Rep:
    def __init__(self, fitness):
        self.fitness = fitness
        self.verdict = "playable"
        self.fidelity = "high"
        self.field_wr = fitness


def main():
    failures = []

    def check(cond, msg):
        print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
        if not cond:
            failures.append(msg)

    pool = make_pool()
    packages = make_packages()
    seed = assemble("gw_core", ["gw_eng"], pool, packages, validate_mana=False)
    check(seed.main_count() == 60, "seed deck is 60 cards")

    # fitness rewards a cheaper curve (lower avg cmc) -> mutations can improve it
    def fit(cand):
        return Rep(round(100.0 - _avg_cmc(cand, pool) * 10.0, 3))

    # --- mutation operators keep the deck legal --------------------------
    rng = random.Random(7)
    for op in (mut_swap_card, mut_adjust_count, mut_swap_support, mut_resolve_mana):
        produced = None
        for _ in range(20):
            child = op(seed, pool, packages, rng)
            if child is not None:
                produced = child
                break
        if produced is not None:
            check(produced.main_count() == 60, f"{op.__name__} yields a 60-card deck")
            over = [n for n, q in produced.mainboard.items()
                    if q > 4 and not (pool.get(n) and pool.get(n).is_land)]
            check(not over, f"{op.__name__} respects the 4-of rule")
        else:
            print(f"  note  {op.__name__} produced no change in 20 tries (acceptable)")

    # --- hill climb improves (or holds) and never regresses --------------
    seed_fit = fit(seed).fitness
    with tempfile.TemporaryDirectory() as d:
        lin = Lineage("testrun", base_dir=d)
        history = []
        best, rep = hill_climb(seed, pool, packages, fit, rounds=60,
                               rng=random.Random(3), lineage=lin,
                               on_step=lambda *a: history.append(a[3]))
        check(best.main_count() == 60, "hill-climb result is a legal 60")
        check(rep.fitness >= seed_fit, f"hill-climb never regresses ({seed_fit} -> {rep.fitness})")
        check(rep.fitness > seed_fit, f"hill-climb found an improvement ({seed_fit} -> {rep.fitness})")
        # best-so-far is monotonic non-decreasing
        check(all(history[i] <= history[i + 1] + 1e-9 for i in range(len(history) - 1)),
              "best-so-far is monotonic non-decreasing")
        check(os.listdir(lin.dir), "lineage nodes were written to disk")

    # --- evolve runs, returns a legal best, mines notations --------------
    store = NotationStore()
    best_e, rep_e, store = evolve([seed], pool, packages, fit, generations=3,
                                  pop_size=6, rng=random.Random(5),
                                  notation_store=store)
    check(best_e is not None and best_e.main_count() == 60, "evolve returns a legal 60")
    check(len(store) > 0, f"evolve recorded notations ({len(store)} pairs)")

    # --- parallel_eval serial path ---------------------------------------
    reports = evaluate_population([seed, best_e], fit, max_workers=1)
    check(len(reports) == 2 and all(r is not None for r in reports),
          "evaluate_population scores all candidates serially")

    # --- leaderboard persistence -----------------------------------------
    with tempfile.TemporaryDirectory() as d:
        lb_path = os.path.join(d, "leaderboard.json")
        update_leaderboard([{"deck_id": "a", "fitness": 50.0, "verdict": "weak", "fidelity": "high"}],
                           path=lb_path)
        merged = update_leaderboard(
            [{"deck_id": "b", "fitness": 70.0, "verdict": "strong", "fidelity": "high"},
             {"deck_id": "a", "fitness": 40.0, "verdict": "weak", "fidelity": "high"}],
            path=lb_path)
        check(merged[0]["deck_id"] == "b", "leaderboard ranks by fitness")
        check(any(e["deck_id"] == "a" and e["fitness"] == 50.0 for e in merged),
              "leaderboard keeps the best score per deck (no regression)")

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s)")
        sys.exit(1)
    print("All optimizer checks passed.")


if __name__ == "__main__":
    main()
