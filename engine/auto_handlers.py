"""engine/auto_handlers.py — bind oracle-parser output to engine events.

Wraps the oracle parser into effect-callable handlers that the engine
can register per card. Populates the existing registries
(`ETB_EFFECTS`, `SPELL_EFFECTS`, etc.) with auto-generated functions
for every card whose effects the parser can understand.

Flow:
  1. `auto_register_for_cards(names)` looks each card up via CardDB
  2. Parses oracle text → trigger → effect list
  3. For each trigger, registers a handler in the appropriate registry
  4. Handlers close over the effect list and call run_effects at fire time

Hand-written handlers take precedence: we skip any card already in a
registry so the curated logic (Bringer, Harvester, Overlord trio, etc.)
is never clobbered.
"""

from __future__ import annotations
from typing import Iterable

from engine.oracle_parser import parse_oracle
from engine.effect_primitives import run_effects


def _make_handler(effects: list, trigger: str):
    """Wrap an effect list into a (gs, card) handler callable."""
    def _handler(gs, card):
        ctx = {"source_card": card, "trigger_event": trigger,
               "chosen_target": None}
        run_effects(gs, ctx, effects)
    _handler.__name__ = f"_auto_{trigger}"
    return _handler


def _make_spell_handler(effects: list):
    """Wrap for SPELL_EFFECTS signature (gs, card) where card is the
    spell that just resolved."""
    def _handler(gs, card):
        ctx = {"source_card": card, "trigger_event": "spell",
               "chosen_target": None}
        run_effects(gs, ctx, effects)
    _handler.__name__ = "_auto_spell"
    return _handler


def auto_register_for_cards(card_names: Iterable[str], verbose: bool = False):
    """Look up each card and wire parser-derived handlers into the
    engine registries. Hand-written entries are preserved.

    Returns a dict of stats:
      {'registered': N, 'skipped_handwritten': M, 'no_effect': K,
       'not_found': J}"""
    from engine.card_db import CardDB
    from engine.card_effects import ETB_EFFECTS, SPELL_EFFECTS

    db = CardDB()
    stats = {"registered": 0, "skipped_handwritten": 0,
             "no_effect": 0, "not_found": 0, "per_trigger": {}}
    for name in card_names:
        data = db.get(name)
        if not data:
            stats["not_found"] += 1
            if verbose:
                print(f"  NOT FOUND: {name}")
            continue
        oracle = data.get("oracle_text") or ""
        # DFC faces: some cards store text at face level
        if not oracle and data.get("card_faces"):
            oracle = "\n".join(f.get("oracle_text", "")
                               for f in data["card_faces"]
                               if f.get("oracle_text"))
        parsed = parse_oracle(oracle, card_name=name)
        if not parsed:
            stats["no_effect"] += 1
            continue

        for trig, effects in parsed.items():
            if not effects:
                continue
            # Route to the right registry
            if trig == "etb" or trig == "etb_or_attack":
                if name in ETB_EFFECTS:
                    stats["skipped_handwritten"] += 1
                    continue
                ETB_EFFECTS[name] = _make_handler(effects, trig)
                stats["registered"] += 1
            elif trig == "spell":
                if name in SPELL_EFFECTS:
                    stats["skipped_handwritten"] += 1
                    continue
                SPELL_EFFECTS[name] = _make_spell_handler(effects)
                stats["registered"] += 1
            # attack / upkeep / endstep / dies / landfall — logged for
            # now; these registries don't exist yet. Track for report.
            stats["per_trigger"][trig] = stats["per_trigger"].get(trig, 0) + 1
    return stats


def auto_register_all_standard_matrix():
    """Convenience: scan the 13 matrix decks and auto-register every
    unique card."""
    import re
    import os
    deck_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "decks")
    names = set()
    for fn in os.listdir(deck_dir):
        if not fn.endswith("_standard.txt"):
            continue
        with open(os.path.join(deck_dir, fn), encoding="utf-8") as f:
            for line in f:
                m = re.match(r"(\d+)\s+(.+)", line.strip())
                if m:
                    names.add(m.group(2).strip())
    return auto_register_for_cards(names, verbose=False)
