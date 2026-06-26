"""
tests/test_anchor_amulet.py -- Phase 6 anchor regression guard.

Builds Amulet Titan from its seed package, runs the full pipeline (real APL +
goldfish sim), and asserts the pipeline scores a KNOWN-GOOD deck as good: not
"ass", and with a kill band that overlaps the measured `amulet` clock in
sim_bridge.ARCHETYPE_CLOCKS.

Requires the oracle DB; skips cleanly (exit 0) when it is absent so it is safe
in a data-less container. This is the end-to-end guard that the whole pipeline
rates a real competitive deck as competitive.

Run: python tests/test_anchor_amulet.py
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from gen.card_pool import CardPool, ORACLE_PATH
from gen.package_schema import load_all_packages
from gen.generator import assemble


def _clock_avg(clock):
    """Expected kill turn of a (possibly sub-100) clock distribution."""
    tot = sum(clock.values())
    return sum(t * p for t, p in clock.items()) / tot if tot else 0.0


def main():
    if not os.path.exists(ORACLE_PATH):
        print("SKIP: oracle DB not present; anchor test requires real card data.")
        print("      Run scripts/fetch_scryfall_bulk.sh in a networked environment.")
        return 0

    failures = []

    def check(cond, msg):
        print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
        if not cond:
            failures.append(msg)

    from sim_bridge import ARCHETYPE_CLOCKS
    from gen.fitness import evaluate

    packages = load_all_packages()
    pool = CardPool.load_or_build("modern")

    # Amulet wants its bounce lands + green ramp; pass explicitly (bounce lands
    # are GUR identity, which auto_supports would conservatively skip).
    supports = [s for s in ("amulet_bounce_lands", "green_ramp_engine", "green_mana_dorks")
                if s in packages]
    cand = assemble("amulet_titan_core", supports, pool, packages, validate_mana=True,
                    name="Anchor Amulet Titan")
    check(cand.main_count() == 60, f"anchor deck is a legal 60 ({cand.main_count()})")

    rep = evaluate(cand, packages=packages, fmt="modern", n_goldfish=3000)
    print(f"\n  verdict={rep.verdict} fitness={rep.fitness} field_wr={rep.field_wr}% "
          f"avg_kill={rep.goldfish.get('avg_kill_turn')} apl={rep.apl_source}")

    # A known-good deck must not be judged "ass".
    check(rep.verdict != "ass", f"known-good Amulet not judged 'ass' (got {rep.verdict})")

    # Kill band overlaps the measured amulet clock (generous +/-3 turns).
    measured_avg = _clock_avg(ARCHETYPE_CLOCKS["amulet"])
    our_avg = rep.goldfish.get("avg_kill_turn")
    if our_avg is not None:
        check(abs(our_avg - measured_avg) <= 3.0,
              f"avg kill turn {our_avg:.1f} within +/-3 of measured {measured_avg:.1f}")
    else:
        check(False, "anchor deck produced no kills (avg_kill_turn is None)")

    print()
    if failures:
        print(f"ANCHOR FAILED: {len(failures)} check(s)")
        sys.exit(1)
    print("Anchor regression passed: pipeline rates Amulet Titan as competitive.")
    return 0


if __name__ == "__main__":
    main()
