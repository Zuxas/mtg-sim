"""Emeritus of Conflict — {1}{R} 2/2 Creature — Human Wizard

Oracle:
  First strike
  Whenever you cast your third spell each turn, this creature becomes
  prepared. (While it's prepared, you may cast a copy of Lightning Bolt.
  Doing so unprepares it.)

Note: Double-faced card. The back face is Lightning Bolt. "Its spell"
= Lightning Bolt (the back face spell). After casting 3 spells in a turn,
you get a free Lightning Bolt (3 damage to any target). Single-use per
activation: once you cast the free Bolt, the creature is unprepared.

Decks: Izzet Cauldron, any Standard Izzet/red spells deck.

Key decisions:
- Cast T2 (1R, 2/2 first strike = good attacker)
- Track spells_this_turn to know when the 3rd-spell trigger fires
- When prepared: use the free Lightning Bolt before end of turn
- Priority: bolt opponent's face if lethal/near-lethal, else kill threat
- Multiple Emeritus of Conflict: each one becomes prepared independently

Spec: apl/card_specs/emeritus_of_conflict.py
"""
from __future__ import annotations

NAME = "Emeritus of Conflict"
CMC = 2   # {1}{R}
BOLT_DAMAGE = 3


def cast(gs, opponent=None) -> bool:
    """Cast Emeritus as early as T2. 2/2 first strike is solid aggro.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            gs._log(f"  Emeritus of Conflict: 2/2 first strike, "
                    f"3rd spell each turn = free Lightning Bolt")
            return True
    return False


def check_prepared(gs, opponent=None) -> bool:
    """Fire the free Lightning Bolt if Emeritus is prepared (3+ spells cast).

    Should be called after casting each spell.
    Returns True if the Bolt was cast.
    """
    emeriti = [c for c in gs.zones.battlefield if c.name == NAME]
    if not emeriti:
        return False

    spells_this_turn = getattr(gs, 'noncreature_spells_this_turn', 0)
    # Prepared condition: 3 or more spells cast this turn
    # (The spell that triggered prepared is included in the count)
    if spells_this_turn < 3:
        return False

    # Only fire once per emeritus (track via a flag on the card)
    for em in emeriti:
        if getattr(em, '_prepared_used', False):
            continue
        # Use the free Lightning Bolt
        em._prepared_used = True
        gs.damage_dealt += BOLT_DAMAGE
        if opponent:
            pass  # damage goes to opponent face or their creature
        gs._log(f"  Emeritus prepared: free Lightning Bolt = "
                f"{BOLT_DAMAGE} damage ({gs.damage_dealt} total)")
        return True
    return False


def reset_prepared_flags(gs) -> None:
    """Call at start of turn to reset prepared state."""
    for c in gs.zones.battlefield:
        if c.name == NAME:
            c._prepared_used = False


def count_on_board(gs) -> int:
    """How many Emeritus of Conflict are on the battlefield."""
    return sum(1 for c in gs.zones.battlefield if c.name == NAME)
