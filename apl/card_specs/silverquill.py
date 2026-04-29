"""Silverquill, the Disputant — {2}{W}{B} 4/4 Legendary Creature — Elder Dragon

Oracle:
  Flying, vigilance
  Each instant and sorcery spell you cast has casualty 1. (As you cast
  that spell, you may sacrifice a creature with power 1 or greater.
  When you do, copy the spell and you may choose new targets for the copy.)

Decks: Jeskai Control variants, Esper builds, any W/B spells deck.

Key decisions:
- Cast T4 (3 mana). Flying/vigilance = attacks AND blocks.
- Casualty 1: sacrifice a 1+ power creature to copy your next spell.
  Best targets: token creatures, small utility creatures (Ragavan, etc.)
- With Veyran: casualty copy triggers Veyran's doubling = extra triggers
- Priority order: save creatures with 1 power as casualty fodder
  rather than attacking into blockers

Spec: apl/card_specs/silverquill.py
"""
from __future__ import annotations
from data.card import Tag
from engine.match_state import safe_power

NAME = "Silverquill, the Disputant"
CMC = 4  # {2}{W}{B}


def cast(gs, opponent=None) -> bool:
    """Cast Silverquill. Flying/vigilance 4/4 at CMC 4 is strong on its own.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            gs._log(f"  Silverquill: 4/4 flying vigilance, all spells have casualty 1")
            return True
    return False


def is_active(gs) -> bool:
    """True if Silverquill is on the battlefield."""
    return any(c.name == NAME for c in gs.zones.battlefield if not c.is_land())


def get_casualty_target(gs) -> object:
    """Find the best creature to sacrifice for casualty 1.

    Priority: tokens (no card disadvantage) > weakest non-essential creature.
    Returns the Card object, or None if no valid target.
    """
    if not is_active(gs):
        return None
    # Creatures with power >= 1 that can be sacrificed
    candidates = [c for c in gs.zones.battlefield
                  if c.has(Tag.CREATURE) and not c.is_land()
                  and safe_power(c) >= 1
                  and c.name != NAME]  # don't sac Silverquill itself
    if not candidates:
        return None
    # Prefer tokens (smallest power, least card value)
    tokens = [c for c in candidates if 'Token' in (getattr(c, 'type_line', '') or '')]
    if tokens:
        return min(tokens, key=lambda c: safe_power(c))
    # Otherwise weakest creature
    return min(candidates, key=lambda c: safe_power(c))


def use_casualty(gs, spell_name: str = "spell") -> bool:
    """Sacrifice a creature for casualty 1 to copy a spell.

    Returns True if a creature was sacrificed (spell will be copied).
    """
    target = get_casualty_target(gs)
    if not target:
        return False
    gs.zones.battlefield.remove(target)
    gs.zones.graveyard.append(target)
    gs._log(f"  Casualty 1: sacrifice {target.name} to copy {spell_name}")
    return True
