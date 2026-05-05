"""scripts/verify_sb_plans.py — validate that every card name in each
deck's SB_PLANS actually exists in its sideboard (for sb_in) or
mainboard (for sb_out). Flags typos / stale references."""
import os
import sys
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from scripts.calibrate_matrix import DECKS
import importlib


def parse_deck(path):
    """Returns (mainboard_names, sideboard_names) as sets."""
    main, side = set(), set()
    in_side = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            if line.lower() == "sideboard":
                in_side = True
                continue
            m = re.match(r"(\d+)\s+(.+)", line)
            if not m:
                continue
            name = m.group(2).strip()
            (side if in_side else main).add(name)
    return main, side


def parse_sb_plan_line(line):
    """'2 Lightning Helix' → 'Lightning Helix'"""
    m = re.match(r"(\d+)\s+(.+)", line.strip())
    return m.group(2).strip() if m else line


issues = []
for label, mod_name, cls_name, deck_path in DECKS:
    print(f"\n=== {label} ({deck_path})")
    main, side = parse_deck(deck_path)
    try:
        mod = importlib.import_module(mod_name)
        cls = getattr(mod, cls_name)
        plans = getattr(cls, "SB_PLANS", {})
    except Exception as e:
        print(f"  !! could not load APL: {e}")
        continue
    for matchup, (sb_in, sb_out) in plans.items():
        for line in sb_in:
            name = parse_sb_plan_line(line)
            if name not in side:
                issues.append((label, matchup, "sb_in", name, "not in SIDEBOARD"))
                print(f"  vs {matchup:10s} IN  missing: {name}")
        for line in sb_out:
            name = parse_sb_plan_line(line)
            if name not in main:
                issues.append((label, matchup, "sb_out", name, "not in MAINBOARD"))
                print(f"  vs {matchup:10s} OUT missing: {name}")

print(f"\n===== SUMMARY =====")
print(f"Total issues: {len(issues)}")
