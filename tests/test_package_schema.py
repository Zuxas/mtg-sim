"""
tests/test_package_schema.py -- Phase 1 tests for packages + notation store.

Structural validation runs against the real seed packages (no card data needed).
Pool-dependent validation (legality / simulatability / color identity) runs
against the hermetic fixture pool. NotationStore behavior is exercised directly.

Run: python tests/test_package_schema.py
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from engine.card_db import CardDB
from gen.card_pool import CardPool
from gen.package_schema import Package, load_all_packages, conjoin_graph
from gen.notation import NotationStore, canonical

FIXTURE_DIR = os.path.join(REPO, "tests", "fixtures", "rules_reference")


def main():
    failures = []

    def check(cond, msg):
        print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
        if not cond:
            failures.append(msg)

    # --- real seed packages: structural integrity ------------------------
    pkgs = load_all_packages()
    check(len(pkgs) >= 8, f"loaded {len(pkgs)} seed packages")
    for pid, pkg in pkgs.items():
        issues = pkg.structural_issues()
        check(not issues, f"{pid} structurally valid" + (f" -> {issues}" if issues else ""))

    # round-trip serialization
    sample = next(iter(pkgs.values()))
    check(Package.from_dict(sample.to_dict()).to_dict() == sample.to_dict(),
          "Package to_dict/from_dict round-trips")

    # at least one core of each kind exists
    roles = {p.role for p in pkgs.values()}
    check("combo-core" in roles and "aggro-core" in roles, "has combo and aggro cores")
    check("engine" in roles and "interaction" in roles and "mana" in roles,
          "has engine, interaction, mana packages")

    # --- conjoin graph: cross-archetype edges ----------------------------
    graph = conjoin_graph(pkgs)
    check(graph.get("amulet_titan_core", set()) and
          "green_ramp_engine" in graph["amulet_titan_core"],
          "amulet core conjoins to green ramp engine (via tag)")
    # green_ramp tag links the green-ramp engine to the Golgari core -> a
    # discoverable cross-archetype bridge.
    check("green_ramp_engine" in graph.get("yawgmoth_sac_core", set()),
          "yawgmoth core bridges to green ramp engine (cross-archetype edge)")
    check(all(pid not in nbrs for pid, nbrs in graph.items()), "no self-edges in conjoin graph")

    # --- pool-dependent validation against the fixture pool --------------
    db = CardDB(rules_dir=FIXTURE_DIR)
    pool = CardPool.build("modern", db=db)

    good = Package(id="t_good", name="t", role="aggro-core",
                   cards={"Grizzly Bears": 2, "Serra Angel": 1},
                   color_identity=["G", "W"], min_slots=3, max_slots=3)
    check(not good.pool_issues(pool), "valid fixture package has no pool issues")
    good.compute_metrics(pool)
    check(good.avg_cmc > 0 and good.pip_demand, f"compute_metrics filled metrics ({good.pip_demand}, cmc {good.avg_cmc})")

    illegal = Package(id="t_illegal", name="t", role="engine",
                      cards={"Black Lotus": 1}, color_identity=[],
                      min_slots=1, max_slots=1)
    check(any("not in" in i for i in illegal.pool_issues(pool)),
          "illegal card flagged by pool_issues")

    under = Package(id="t_under", name="t", role="aggro-core",
                    cards={"Serra Angel": 1}, color_identity=["G"],
                    min_slots=1, max_slots=1)
    check(any("color_identity" in i for i in under.pool_issues(pool)),
          "under-declared color identity flagged")

    unsim = Package(id="t_unsim", name="t", role="engine",
                    cards={"Mysterious Tinkerer": 1}, color_identity=["U"],
                    min_slots=1, max_slots=1, requires_simulatable=True)
    check(any("not simulatable" in i for i in unsim.pool_issues(pool)),
          "requires_simulatable flags an unhandled (HAS_EFFECTS) card")
    unsim.requires_simulatable = False
    check(not unsim.pool_issues(pool), "same card OK when requires_simulatable is False")

    # --- NotationStore ---------------------------------------------------
    store = NotationStore()
    store.record(("Amulet of Vigor", "Primeval Titan"), 6.0, deck_id="d1")
    store.record(("Amulet of Vigor", "Primeval Titan"), 8.0, deck_id="d2")
    nt = store.get(("Primeval Titan", "Amulet of Vigor"))   # order-independent
    check(nt is not None and nt.observations == 2, "notation records and is order-independent")
    check(6.0 < nt.strength < 8.0, f"EWMA strength between observations ({nt.strength:.2f})")
    check(store.record(("Solo Card",), 5.0) is None, "single-card notation rejected")

    store.record(("Yawgmoth, Thran Physician", "Walking Ballista"), 9.0, deck_id="d3")
    top = store.top(1)
    check(top and top[0].cards == canonical(("Yawgmoth, Thran Physician", "Walking Ballista")),
          "top() returns strongest notation")

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "notations.json")
        store.save(path)
        reloaded = NotationStore.load(path)
        check(len(reloaded) == len(store), "NotationStore save/load round-trips")
        check(reloaded.get(("Amulet of Vigor", "Primeval Titan")) is not None,
              "reloaded notation present")

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s)")
        sys.exit(1)
    print("All package + notation checks passed.")


if __name__ == "__main__":
    main()
