"""Quantum Riddler — `{3}{U}{U}` 4/6 flying.

Oracle:
  When Quantum Riddler enters, you may draw a card.

Decks using this spec: Jeskai Blink (4), UW Blink (3), Esper Blink (4).

Reference impl: apl/jeskai_blink_match.py:227-231; apl/uw_blink_match.py
inline cast.

Spec: harness/specs/2026-04-29-card-specs-framework.md
"""
from __future__ import annotations

NAME = "Quantum Riddler"
CMC = 5  # {3}{U}{U}


def cast(gs, opponent=None) -> bool:
    """Cast Quantum Riddler if mana available. Triggers ETB draw 1.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            # ETB draw 1 (engine may or may not auto-fire)
            gs.zones.draw(1)
            return True
    return False


def blink_etb(gs, opponent=None) -> None:
    """Re-fire Quantum Riddler's ETB on blink (Phelia attack, Ephemerate).

    Called by blink mechanism after the creature re-enters from exile.
    """
    gs.zones.draw(1)
    gs._log(f"  Blink-ETB Quantum Riddler: draw 1")
