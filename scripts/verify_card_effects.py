"""scripts/verify_card_effects.py — audit every registered card effect
against the Scryfall oracle text.

For each card registered in ETB_EFFECTS / SPELL_EFFECTS / SAGA_EFFECTS /
CLASS_DEFS / LANDFALL / _LORD_EFFECTS / _COST_REDUCTIONS / MATCH_REMOVAL,
print:
  1. the card's oracle-text snapshot
  2. the registry it's in
  3. a summary of what the registered handler actually does

You eyeball the diff and flag anything wrong."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
import sys
sys.path.insert(0, str(ROOT))

ORACLE_PATH = ROOT / "data" / "rules_reference" / "scryfall_oracle_cards.json"
with open(ORACLE_PATH, encoding="utf-8") as f:
    raw = json.load(f)
CARDS = raw if isinstance(raw, list) else raw.get("data", [])

BY_NAME = {c["name"]: c for c in CARDS if "name" in c}
# Index DFC faces by front-face name so "Kumano Faces Kakkazan"
# matches even though the card's full name is the double-sided form.
BY_FACE = {}
for c in CARDS:
    for face in c.get("card_faces", []):
        fname = face.get("name")
        if fname:
            merged = {**c, **face}
            BY_FACE.setdefault(fname, merged)


def oracle(name):
    c = BY_NAME.get(name) or BY_FACE.get(name)
    if not c:
        return None
    return {
        "cost": c.get("mana_cost", ""),
        "cmc": c.get("cmc"),
        "type": c.get("type_line", ""),
        "pt":   f"{c.get('power','')}/{c.get('toughness','')}",
        "text": (c.get("oracle_text") or "").replace("\n", " | "),
    }


# Pull registered handlers
from engine.card_effects import (
    ETB_EFFECTS, SPELL_EFFECTS, LANDFALL_GROW,
    LANDFALL_TOKEN, LANDFALL_ASCENSION,
)
from engine.sagas import SAGA_EFFECTS
from engine.classes import CLASS_DEFS
from engine.game_state import _LORD_EFFECTS, _COST_REDUCTIONS
from engine.match_state import _CONDITIONAL_EVASION
from apl.match_apl import MatchAPL


def fmt(card_name, registry_label):
    o = oracle(card_name)
    if o is None:
        return f"[{registry_label}] {card_name:40s}  *** NOT IN ORACLE CACHE ***"
    return (f"[{registry_label}] {card_name}\n"
            f"    cost={o['cost']:15s} cmc={o['cmc']} "
            f"type={o['type']}  pt={o['pt']}\n"
            f"    text={o['text'][:180]}\n")


sections = [
    ("ETB_EFFECTS", ETB_EFFECTS.keys()),
    ("SPELL_EFFECTS", SPELL_EFFECTS.keys()),
    ("SAGA_EFFECTS", SAGA_EFFECTS.keys()),
    ("CLASS_DEFS", CLASS_DEFS.keys()),
    ("LORD_EFFECTS", _LORD_EFFECTS.keys()),
    ("COST_REDUCTIONS", _COST_REDUCTIONS.keys()),
    ("CONDITIONAL_EVASION", _CONDITIONAL_EVASION.keys()),
    ("LANDFALL_GROW", LANDFALL_GROW),
    ("LANDFALL_TOKEN", LANDFALL_TOKEN),
    ("LANDFALL_ASCENSION", LANDFALL_ASCENSION),
    ("MATCH_REMOVAL", MatchAPL.MATCH_REMOVAL.keys()),
]

for label, names in sections:
    print(f"\n======  {label}  ======")
    for name in sorted(names):
        print(fmt(name, label))
