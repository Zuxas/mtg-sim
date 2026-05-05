"""scripts/verify_decks.py — verify every card in every matrix deck
against CardDB. Flags cards that fail lookup or return empty data."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from engine.card_db import CardDB
from scripts.calibrate_matrix import DECKS
from data.deck import load_deck_from_file

db = CardDB()

issues = []
seen_cards = set()
for label, _mod, _cls, deck_path in DECKS:
    print(f"\n=== {label}: {deck_path}")
    with open(deck_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//") or line.lower() == "sideboard":
                continue
            # Parse "N Card Name"
            parts = line.split(" ", 1)
            if len(parts) < 2 or not parts[0].isdigit():
                continue
            qty, name = parts[0], parts[1]
            if name in seen_cards:
                continue
            seen_cards.add(name)
            data = db.get(name)
            if not data:
                issues.append((label, name, "NOT FOUND"))
                print(f"  MISS: {name}")
                continue
            cost = data.get("mana_cost", "")
            type_line = data.get("type_line", "")
            text = (data.get("oracle_text") or "").replace("\n", " | ")[:120]
            if not cost and not type_line:
                issues.append((label, name, "EMPTY DATA"))
                print(f"  STUB: {name}")
            elif not text:
                print(f"  OK (no text): {name:40s} cost={cost} type={type_line}")
            else:
                # Short confirmation
                pass

print(f"\n===== SUMMARY =====")
print(f"Unique cards checked: {len(seen_cards)}")
print(f"Issues found: {len(issues)}")
for label, name, reason in issues:
    print(f"  [{label}] {name}: {reason}")
