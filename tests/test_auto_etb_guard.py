"""The handler build takes ETB effects only from a card's own
"When ~ enters, ..." sentences (scripts/build_standard_handlers.py).

Checks the two helpers on real card wordings, and that no registered
auto-generated ETB handler belongs to a card the guard reported as dropped.

Run: python tests/test_auto_etb_guard.py
"""
import csv
import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# The build script runs on import (it needs the bulk file), so lift the two
# pure helpers out of its source instead.
src = open(os.path.join(ROOT, "scripts", "build_standard_handlers.py"), encoding="utf-8").read()
start = src.index('_SELF = r"')
end = src.index("def guard_reason")
ns = {"re": re}
exec(src[start:end], ns)
self_etb_text = ns["self_etb_text"]

# its own enters trigger: kept, with the modes under it
t = self_etb_text("Flying\nWhen Starling enters, choose one —\n• Draw a card.\n• You gain 3 life.\nWard {2}",
                  "Starling, Aerial Ally")
assert t.startswith("When ~ enters") and "Draw a card" in t and "Ward" not in t and "Flying" not in t, t
assert self_etb_text("When this creature enters, draw a card.", "Gallant Citizen")
assert self_etb_text("Whenever this creature enters or attacks, scry 1.", "X")
# not its own enters trigger: nothing
for oracle in (
    "When this creature dies, create a Treasure token.",                       # Common Crook
    "Flying\nWhen this creature leaves the battlefield, create a Food token.",  # City Pigeon
    "Whenever another creature you control enters, you gain 1 life.",          # Aunt May
    "Whenever you cast a spell with mana value 4 or greater, put a +1/+1 counter on this creature.",
    "This creature enters with a +1/+1 counter on it.",
    "At the beginning of your upkeep, draw a card.",
):
    assert self_etb_text(oracle, "Some Card") == "", oracle

# the committed handlers file agrees with the committed report
report = os.path.join(ROOT, "data", "auto_etb_guard_report.csv")
dropped = {r["card"] for r in csv.DictReader(open(report, encoding="utf-8")) if r["new_etb_effects"] == "[]"}
gen = open(os.path.join(ROOT, "engine", "standard_auto_handlers.py"), encoding="utf-8").read()
etb_block = gen[gen.index("for _n,_f in {"):gen.index("}.items(): ETB_EFFECTS")]
registered = set(re.findall(r'^\s*"((?:[^"\\]|\\.)+)":', etb_block, re.M))
assert len(dropped) > 300 and len(registered) > 300
assert not (dropped & registered), sorted(dropped & registered)[:5]
print("test_auto_etb_guard: OK")
