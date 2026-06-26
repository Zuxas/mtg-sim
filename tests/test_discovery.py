"""
tests/test_discovery.py -- Phase 5 tests for discovery + meta synthesis.

Offline, using a synthetic pool/packages and a hand-built NotationStore.

Run: python tests/test_discovery.py
"""

import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from engine.mana import parse_cost
from gen.card_pool import CardPool, PoolCard
from gen.package_schema import Package
from gen.notation import NotationStore
from gen.discovery import mine_packages, propose_archetypes
from gen.meta_synth import synthesize_meta


def _creature(name, color, cmc=2):
    cost = "{1}{" + color + "}"
    return PoolCard(name=name, cmc=cmc, mana_cost=cost, type_line="Creature - Beast",
                    color_identity=[color], colors=[color], pips=parse_cost(cost),
                    is_land=False, sim_bucket="VANILLA", simulatable=True)


def _land(name, tl, ci):
    return PoolCard(name=name, cmc=0.0, mana_cost="", type_line=tl, color_identity=ci,
                    colors=[], pips={"generic": 0}, is_land=True,
                    sim_bucket="VANILLA", simulatable=True)


def make_pool():
    cards = {"Forest": _land("Forest", "Basic Land - Forest", ["G"]),
             "Plains": _land("Plains", "Basic Land - Plains", ["W"]),
             "Mountain": _land("Mountain", "Basic Land - Mountain", ["R"])}
    for color in ("G", "W", "R"):
        for i in range(1, 13):
            n = f"{color} Card {i}"
            cards[n] = _creature(n, color)
    return CardPool("modern", cards)


def make_packages():
    return {
        "gw_core": Package(id="gw_core", name="GW Core", role="aggro-core",
                           cards={"G Card 1": 4, "W Card 1": 4}, color_identity=["G", "W"],
                           conjoins_with=["mid"], tags=["mid"], min_slots=8, max_slots=8),
        "rg_core": Package(id="rg_core", name="RG Core", role="combo-core",
                           cards={"R Card 1": 4, "G Card 2": 4}, color_identity=["R", "G"],
                           conjoins_with=["mid"], tags=["mid"], min_slots=8, max_slots=8),
        "eng": Package(id="eng", name="Engine", role="engine",
                       cards={"G Card 3": 4}, color_identity=["G"],
                       conjoins_with=[], tags=["mid"], min_slots=4, max_slots=4),
        "pay": Package(id="pay", name="Payoff", role="payoff",
                       cards={"G Card 4": 4}, color_identity=["G"],
                       conjoins_with=[], tags=["mid"], min_slots=4, max_slots=4),
    }


def main():
    failures = []

    def check(cond, msg):
        print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
        if not cond:
            failures.append(msg)

    pool = make_pool()
    packages = make_packages()

    # --- mine_packages: a strong card cluster becomes a package ----------
    store = NotationStore()
    # build a 3-card strong cluster G Card 5 - G Card 6 - G Card 7
    for pair in [("G Card 5", "G Card 6"), ("G Card 6", "G Card 7"), ("G Card 5", "G Card 7")]:
        store.record(pair, 5.0, deck_id="d1")
        store.record(pair, 6.0, deck_id="d2")   # 2 observations, strong
    # a weak, single-observation pair that must NOT be promoted
    store.record(("R Card 9", "W Card 9"), 0.2, deck_id="d3")

    mined = mine_packages(store, pool, min_strength=1.0, min_observations=2, run_id="t1")
    check(len(mined) == 1, f"one strong cluster mined ({len(mined)})")
    if mined:
        names = set(mined[0].cards)
        check(names == {"G Card 5", "G Card 6", "G Card 7"},
              f"mined cluster has the right cards ({sorted(names)})")
        check(mined[0].provenance == "discovered:t1", "mined package carries discovered provenance")
        check(not mined[0].structural_issues(), "mined package is structurally valid")
        check("R Card 9" not in names, "weak/under-observed pair excluded")

    # --- propose_archetypes: novel core+support combos -------------------
    seen = {frozenset(["gw_core", "eng"])}    # this combo already piloted
    proposals = propose_archetypes(packages, pool, notation_store=store, seen_sets=seen,
                                   max_proposals=6)
    check(proposals, f"discovery proposed {len(proposals)} archetypes")
    check(all(c.main_count() == 60 for c in proposals), "all proposals are legal 60s")
    pkg_sets = [frozenset(c.packages) for c in proposals]
    check(frozenset(["gw_core", "eng"]) not in pkg_sets, "already-seen combo not re-proposed")
    check(any(c.packages[0] == "rg_core" for c in proposals), "explores the RG core too")

    # --- meta synthesis --------------------------------------------------
    entries = [
        {"deck_id": "Aggro", "fitness": 70.0, "color_identity": ["R"],
         "packages": ["rg_core"], "kill_distribution": {3: 60.0, 4: 30.0, 5: 10.0}},
        {"deck_id": "Midrange", "fitness": 60.0, "color_identity": ["G", "W"],
         "packages": ["gw_core"], "kill_distribution": {5: 40.0, 6: 40.0, 7: 20.0}},
        {"deck_id": "Control", "fitness": 55.0, "color_identity": ["U", "W"],
         "packages": ["uw_core"], "kill_distribution": {8: 50.0, 9: 30.0, 10: 20.0}},
    ]
    with tempfile.TemporaryDirectory() as d:
        report = synthesize_meta(entries, top_n=3, run_id="t1", out_dir=d, n_race=8000)
        check(len(report["field"]) == 3, "meta field has 3 distinct decks")
        check(abs(sum(report["shares"].values()) - 100.0) < 0.5, "shares sum to ~100")
        # the fast aggro deck should out-race the slow control deck head to head
        check(report["matrix"]["Aggro"]["Control"] > 80.0,
              "fast aggro beats slow control in the race matrix")
        check(report["matrix"]["Aggro"]["Aggro"] == 50.0, "mirror is 50%")
        check(os.path.exists(report["_path"]), "meta report written to disk")

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s)")
        sys.exit(1)
    print("All discovery + meta-synthesis checks passed.")


if __name__ == "__main__":
    main()
