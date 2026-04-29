"""Prismari, the Inspiration — {5}{U}{R} 7/7 Legendary Creature — Elder Dragon

Oracle:
  Flying
  Ward—Pay 5 life.
  Instant and sorcery spells you cast have storm. (Whenever you cast an
  instant or sorcery spell, copy it for each spell cast before it this
  turn. You may choose new targets for the copies.)

Decks: Izzet Cauldron, any Standard spells deck.

Key decisions:
- Cast T6+ when you can also cast at least one spell the same turn
  (storm baseline = 1 copy minimum when prior spell cast this turn)
- Ward 5 life is strong protection; opponent pays 5 life to target it
- With Veyran: storm triggers again = 2× copies per storm trigger
- Sequencing: cast cheap spells BEFORE Prismari to maximize storm count
  e.g. T6: Opt → Prismari (storm = 1 copy) → bolt (storm = 2 copies)

Spec: apl/card_specs/prismari.py
"""
from __future__ import annotations
from data.card import Tag

NAME = "Prismari, the Inspiration"
CMC = 7  # {5}{U}{R}


def cast(gs, opponent=None) -> bool:
    """Cast Prismari when we have mana + at least 1 prior spell this turn.

    Goldfish: cast as soon as affordable (7 mana, T6-7).
    Match: cast when spells_this_turn >= 1 to guarantee at least 1 storm copy.
    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            spells_prior = getattr(gs, 'noncreature_spells_this_turn', 0)
            # Cast even without prior spells — 7/7 flier is strong alone
            # But prefer to cast after at least one spell for storm value
            gs.cast_spell(c)
            gs._log(f"  Prismari: 7/7 flying ward-5-life, storm on all spells "
                    f"(prior spells this turn: {spells_prior})")
            return True
    return False


def storm_copies(gs) -> int:
    """How many storm copies would the next instant/sorcery produce?

    Equal to noncreature_spells_this_turn (spells cast before this one).
    Used by APL to evaluate whether casting a spell now is worth delaying
    vs casting it later for more copies.
    """
    return getattr(gs, 'noncreature_spells_this_turn', 0)


def is_active(gs) -> bool:
    """True if Prismari is on the battlefield (storm applies to spells)."""
    return any(c.name == NAME for c in gs.zones.battlefield if not c.is_land())


def apply_storm_damage(gs, spell_damage: int, opponent=None) -> int:
    """Calculate total damage from a burn spell with storm copies.

    Args:
        spell_damage: base damage of the spell (e.g. 3 for Lightning Bolt)
        opponent: opponent state (needed to deal damage)

    Returns total damage dealt (spell_damage × (1 + storm_copies)).
    """
    if not is_active(gs):
        return spell_damage
    copies = storm_copies(gs)
    total = spell_damage * (1 + copies)
    if opponent and total > 0:
        gs.damage_dealt += total
        gs._log(f"  Storm: {1 + copies}× copies = {total} total damage")
    return total
