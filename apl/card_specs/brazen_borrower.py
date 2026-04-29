"""Brazen Borrower // Petty Theft — {1}{U}{U} 3/1 Legendary Creature — Faerie Rogue

Oracle:
  Flash
  Flying
  This creature can block only creatures with flying.
  ---
  Petty Theft {1}{U} (Adventure)
  Return target nonland permanent an opponent controls to its owner's hand.

Decks: Jeskai Control, Izzet Control, any Standard blue deck.

Key decisions:
- Petty Theft first: {1}{U} at instant speed to bounce opponent's best
  permanent (creature, planeswalker, enchantment). Buys a turn.
  Then later cast the 3/1 from exile.
- 3/1 flash flying: can be cast at instant speed to surprise block a
  flying attacker, or as a threat after using Petty Theft.
- Sequencing: Petty Theft first (T2), then creature part later when
  opponent rebuilds. Or flash in as surprise blocker for a flier.
- vs Affinity: bounce Kappa Cannoneer (resets ward/counters).
- vs Amulet Titan: bounce Primeval Titan before attack trigger.
- Can only block fliers: don't rely on it to stop ground threats.

Spec: apl/card_specs/brazen_borrower.py
"""
from __future__ import annotations
from data.card import Tag
from engine.match_state import safe_power

NAME = "Brazen Borrower"
ADVENTURE_NAME = "Petty Theft"
CMC = 3   # {1}{U}{U} for the creature
ADV_CMC = 2  # {1}{U} for Petty Theft


def cast_adventure(gs, opponent=None) -> bool:
    """Cast Petty Theft to bounce opponent's best nonland permanent.

    Returns True if cast.
    """
    if not opponent:
        return False
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.total() >= ADV_CMC:
            # Find best target to bounce
            targets = [x for x in opponent.zones.battlefield
                       if not x.is_land()]
            if not targets:
                return False
            target = max(targets, key=lambda x: getattr(x, 'cmc', 0))
            try:
                gs.mana_pool.pay("{1}{U}", ADV_CMC)
            except Exception:
                return False
            # Bounce target to hand
            opponent.zones.battlefield.remove(target)
            opponent.zones.hand.append(target)
            # Move Brazen Borrower to exile (adventure zone — will be cast as creature later)
            gs.zones.hand.remove(c)
            gs.zones.exile.append(c)
            gs._log(f"  Petty Theft: bounce {target.name} to hand "
                    f"(Borrower in exile, ready to cast)")
            return True
    return False


def cast_creature(gs, opponent=None) -> bool:
    """Cast the 3/1 flash flying creature (from hand or exile after adventure).

    Returns True if cast.
    """
    # Check exile first (post-adventure)
    for zone in (gs.zones.exile, gs.zones.hand):
        for c in list(zone):
            if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                zone.remove(c)
                gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                c.summoning_sickness = False  # Flash = not summoning sick
                gs._log(f"  Brazen Borrower: 3/1 flash flying")
                return True
    return False


def should_bounce(gs, opponent, target) -> bool:
    """Heuristic: is this permanent worth bouncing with Petty Theft?"""
    if not target or target.is_land():
        return False
    cmc = getattr(target, 'cmc', 0)
    return cmc >= 3 or 'Planeswalker' in (getattr(target, 'type_line', '') or '')
