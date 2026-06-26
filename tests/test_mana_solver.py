"""
tests/test_mana_solver.py -- Phase 2 tests for the mana solver + generator.

Uses an in-memory synthetic CardPool (constructed PoolCards) so we control a
pool rich enough to fill a 60-card deck without the 37k-card oracle download.

Run: python tests/test_mana_solver.py
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from engine.mana import parse_cost
from gen.card_pool import CardPool, PoolCard
from gen.package_schema import Package
from gen.mana_solver import solve_manabase, castability, colored_demand
from gen.generator import assemble, auto_supports, DeckCandidate

BASICS = {"W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain", "G": "Forest"}


def _creature(name, color, cmc=2):
    cost = "{1}" + "{" + color + "}" if cmc == 2 else "{" + color + "}"
    return PoolCard(name=name, cmc=cmc, mana_cost=cost,
                    type_line="Creature - Beast", color_identity=[color],
                    colors=[color], pips=parse_cost(cost), is_land=False,
                    sim_bucket="VANILLA", simulatable=True)


def _land(name, type_line, identity):
    return PoolCard(name=name, cmc=0.0, mana_cost="", type_line=type_line,
                    color_identity=list(identity), colors=[], pips={"generic": 0},
                    is_land=True, sim_bucket="VANILLA", simulatable=True)


def make_pool():
    cards = {}
    for color, basic in BASICS.items():
        cards[basic] = _land(basic, f"Basic Land - {basic}", [color])
    cards["Temple Garden"] = _land("Temple Garden", "Land - Forest Plains", ["G", "W"])
    cards["Steam Vents"] = _land("Steam Vents", "Land - Island Mountain", ["U", "R"])
    for color in ("W", "G", "R", "U"):
        for i in range(1, 9):
            n = f"{color} Vanilla {i}"
            cards[n] = _creature(n, color, cmc=2 if i % 2 else 3)
    return CardPool("modern", cards)


def main():
    failures = []

    def check(cond, msg):
        print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
        if not cond:
            failures.append(msg)

    pool = make_pool()

    # --- mana solver -----------------------------------------------------
    # Two-color UR spells: both colors must be sourced; dual gets used.
    ur_spells = {"R Vanilla 1": 4, "U Vanilla 1": 4, "R Vanilla 3": 4, "U Vanilla 3": 4}
    base = solve_manabase(ur_spells, pool, total_lands=18)
    check(sum(base.values()) == 18, f"UR manabase sums to 18 (got {sum(base.values())})")
    check("Island" in base and "Mountain" in base, "UR base sources both U and R")
    check(base.get("Steam Vents", 0) > 0, "UR base uses the U/R dual")
    cast_ur = castability(base, ur_spells, pool, trials=1500)
    check(cast_ur >= 0.80, f"UR base clears the castability floor ({cast_ur:.2f})")

    # Mono-green: base is essentially all Forests.
    g_spells = {"G Vanilla 1": 4, "G Vanilla 3": 4, "G Vanilla 5": 4}
    gbase = solve_manabase(g_spells, pool, total_lands=17)
    check(gbase.get("Forest", 0) >= 16, f"mono-G base is mostly Forests ({gbase})")
    check(sum(gbase.values()) == 17, "mono-G base sums to 17")

    # Demand weighting: a cheap double-pip drives more of that color.
    demand = colored_demand({"R Vanilla 1": 4, "G Vanilla 5": 1}, pool)
    check(demand.get("R", 0) > demand.get("G", 0), "cheap heavy color outweighs lone late pip")

    # --- generator: trim path (core has too many spells) -----------------
    big_core = Package(id="gw_big", name="GW Big", role="aggro-core",
                       cards={f"G Vanilla {i}": 4 for i in range(1, 7)},
                       color_identity=["G"], min_slots=24, max_slots=24)
    packages = {"gw_big": big_core}
    cand = assemble("gw_big", [], pool, {"gw_big": big_core}, target_size=60)
    check(cand.main_count() == 60, f"trim-path deck has exactly 60 cards ({cand.main_count()})")
    check(cand.spell_count(pool) + cand.land_count(pool) == 60, "spells + lands == 60")
    check(cand.metadata["fidelity"] == "high", "all-vanilla deck is high fidelity")

    # --- generator: pad path (core too small -> filler) ------------------
    small_core = Package(id="gw_small", name="GW Small", role="aggro-core",
                         cards={"G Vanilla 1": 4, "W Vanilla 1": 4},
                         color_identity=["G", "W"], min_slots=8, max_slots=8)
    support = Package(id="gw_pay", name="GW Payoff", role="payoff",
                      cards={"W Vanilla 3": 4}, color_identity=["G", "W"],
                      conjoins_with=[], tags=["gw"], min_slots=4, max_slots=4)
    pkgs = {"gw_small": small_core, "gw_pay": support}
    cand2 = assemble("gw_small", ["gw_pay"], pool, pkgs, target_size=60)
    check(cand2.main_count() == 60, f"pad-path deck has exactly 60 cards ({cand2.main_count()})")
    check(set(cand2.color_identity) == {"G", "W"}, f"deck CI is GW ({cand2.color_identity})")
    check("castability" in cand2.metadata and cand2.metadata["castability"] > 0.0,
          "candidate has a castability score")
    # no card exceeds 4 copies; basics may exceed.
    over = [n for n, q in cand2.mainboard.items()
            if q > 4 and (pool.get(n) is None or not pool.get(n).is_land)]
    check(not over, "no nonland card exceeds 4 copies")

    # --- DeckCandidate round-trip ----------------------------------------
    rt = DeckCandidate.from_dict(cand2.to_dict())
    check(rt.mainboard == cand2.mainboard, "DeckCandidate to_dict/from_dict round-trips")

    # --- low fidelity flag ----------------------------------------------
    pool._cards["Sketchy Engine"] = PoolCard(
        name="Sketchy Engine", cmc=3, mana_cost="{2}{G}", type_line="Artifact",
        color_identity=["G"], colors=["G"], pips=parse_cost("{2}{G}"),
        is_land=False, sim_bucket="HAS_EFFECTS", simulatable=False)
    bad = Package(id="bad", name="Bad", role="combo-core",
                  cards={"Sketchy Engine": 4, "G Vanilla 1": 4},
                  color_identity=["G"], min_slots=8, max_slots=8,
                  requires_simulatable=False)
    cand3 = assemble("bad", [], pool, {"bad": bad}, target_size=60, validate_mana=False)
    check(cand3.metadata["fidelity"] == "low", "deck with unsimulatable card is low fidelity")
    check("Sketchy Engine" in cand3.metadata["unsimulatable_cards"], "names the unsimulatable card")

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s)")
        sys.exit(1)
    print("All mana-solver + generator checks passed.")


if __name__ == "__main__":
    main()
