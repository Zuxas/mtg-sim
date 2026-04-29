"""Teferi, Time Raveler — `{1}{W}{U}` planeswalker, starts at 4 loyalty.

Oracle:
  Each opponent can cast spells only any time they could cast a sorcery.
  +1: Until your next turn, you may cast sorcery spells as though they
      had flash.
  -3: Return up to one target artifact, creature, or enchantment to its
      owner's hand. Draw a card.

Decks using this spec: Jeskai Blink (2), UW Blink (2), Esper Blink (2).

Goldfish viability: MEDIUM. +1 ability is dead (no opp spells); -3 bounce
target dead (no opp permanent); but the -3 also draws a card which IS
viable. Effectively burns 3 mana for 1 card in goldfish.

Reference impl: apl/jeskai_blink_match.py:241-253.

Spec: harness/specs/2026-04-29-card-specs-framework.md
"""
from __future__ import annotations

NAME = "Teferi, Time Raveler"
CMC = 3  # {1}{W}{U}


def cast(gs, opponent=None) -> bool:
    """Cast Teferi. Goldfish: cast for the -3 draw 1 effect.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            # -3 ability: bounce + draw 1 (bounce target useless in goldfish)
            gs.zones.draw(1)
            gs._log(f"  Teferi -3: draw 1 (bounce no-op in goldfish)")
            return True
    return False
