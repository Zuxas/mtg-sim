"""Only legal, exact sideboard swaps reach the Bo3 sim.
Spec harness/specs/2026-09-30-sideboard-plan-validation.md."""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
import sideboard_plans as sp


def _c(name):
    return Card(name=name, mana_cost="{1}", cmc=1, type_line="Instant", oracle_text="")


MAIN = [_c("Lightning Bolt")] * 4 + [_c("Counterspell")] * 4 + [_c("Island")] * 52
SIDE = [_c("Negate")] * 2 + [_c("Pyroblast")] * 3 + [_c("Tormod's Crypt")] * 10


def test_valid_two_for_two():
    ok, why, sw = sp.validate_plan(MAIN, SIDE, ["2 Negate"], ["2 Lightning Bolt"])
    assert ok, why
    assert sw["in"] == Counter({"Negate": 2}) and sw["out"] == Counter({"Lightning Bolt": 2})


def test_multi_entry_and_case_insensitive_names():
    ok, why, _ = sp.validate_plan(MAIN, SIDE, ["1 negate +2 Pyroblast"], ["3 Counterspell"])
    assert ok, why


def test_rejections():
    cases = {
        "unknown in": (["2 Duress"], ["2 Lightning Bolt"]),
        "unknown out": (["2 Negate"], ["2 Spell Snare"]),
        "short sideboard": (["3 Negate"], ["3 Lightning Bolt"]),
        "too many out": (["3 Pyroblast"], ["3 Lightning Bolt", "2 Lightning Bolt"]),
        "in != out": (["2 Negate"], ["1 Lightning Bolt"]),
        "unparsable pct": (["5.0%"], ["1 Lightning Bolt"]),
        "unparsable word": (["Hard"], []),
        "fuzzy-only name": (["2 Negat"], ["2 Lightning Bolt"]),
        "empty": ([], []),
    }
    for label, (i, o) in cases.items():
        ok, why, _ = sp.validate_plan(MAIN, SIDE, i, o)
        assert not ok, label
        assert why, label


class _Apl:
    def __init__(self, plans, arch):
        self.SB_PLANS, self.ARCHETYPE = plans, arch

    def sb_plan_for(self, a):
        p = self.SB_PLANS.get(a)
        return (list(p[0]), list(p[1])) if p else None


def test_choose_plan_order_and_fallback():
    orig = sp.get_sb_plan
    try:
        sp.get_sb_plan = lambda a, b: (["1 Pyroblast"], ["1 Counterspell"])
        opp = _Apl({}, "aggro")
        good_apl = _Apl({"aggro": (["2 Negate"], ["2 Lightning Bolt"])}, "control")
        bad_apl = _Apl({"aggro": (["2 Duress"], ["2 Lightning Bolt"])}, "control")
        plan, src, _ = sp.choose_plan("Us", "Them", MAIN, SIDE, good_apl, opp)
        assert src == "apl" and plan == (["2 Negate"], ["2 Lightning Bolt"])
        plan, src, _ = sp.choose_plan("Us", "Them", MAIN, SIDE, bad_apl, opp)
        assert src == "playbook" and plan == (["1 Pyroblast"], ["1 Counterspell"])
        sp.get_sb_plan = lambda a, b: (["5.0%"], ["Hard"])
        plan, src, why = sp.choose_plan("Us", "Them", MAIN, SIDE, bad_apl, opp)
        assert plan is None and src == "rejected" and "apl:" in why and "playbook:" in why
        sp.get_sb_plan = lambda a, b: ([], [])
        plan, src, _ = sp.choose_plan("Us", "Them", MAIN, SIDE, None, None)
        assert plan is None and src == "none"
    finally:
        sp.get_sb_plan = orig


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("ALL SIDEBOARD PLAN TESTS PASS")
