"""Rootha, Mastering the Moment — {2}{U}{R} 3/4 Legendary Creature — Orc Sorcerer

Oracle:
  At the beginning of combat on your turn, if you've cast an instant or
  sorcery spell this turn, create an X/X blue and red Elemental creature
  token with flying and haste, where X is the greatest mana value among
  instant and sorcery spells you've cast this turn.

Decks: Izzet Cauldron, Standard Izzet spells.

Key decisions:
- Cast T4 (2UR). 3/4 body is reasonable.
- Combat trigger: BEFORE attacking, if you cast a spell this turn,
  you get an X/X flier haste where X = highest MV spell cast.
- Sequencing: cast your highest-MV spell BEFORE combat for biggest token
  e.g. Cast Magma Opus (MV 8) → get 8/8 flying haste token → attack
  e.g. Cast Lightning Bolt (MV 1) → get 1/1 flying haste token (weak)
- With Prismari (storm): stormed copies count as spells cast,
  but MV is tracked per unique cast not per copy
- Best target MV: aim for spells with MV 4+ for impactful tokens

Spec: apl/card_specs/rootha.py
"""
from __future__ import annotations
from data.card import Card, Tag

NAME = "Rootha, Mastering the Moment"
CMC = 4  # {2}{U}{R}


def cast(gs, opponent=None) -> bool:
    """Cast Rootha. Good as 3/4 body + generates flier haste tokens at combat.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            gs._log(f"  Rootha: 3/4 body, begin-combat trigger creates X/X flier haste")
            return True
    return False


def is_active(gs) -> bool:
    """True if Rootha is on the battlefield."""
    return any(c.name == NAME for c in gs.zones.battlefield if not c.is_land())


def fire_combat_trigger(gs, opponent=None) -> int:
    """Create X/X flying haste token if a spell was cast this turn.

    X = greatest MV among spells cast this turn.
    Returns the X value (token size), or 0 if trigger doesn't fire.
    """
    if not is_active(gs):
        return 0
    # Requires at least one instant/sorcery cast this turn
    spells = getattr(gs, 'noncreature_spells_this_turn', 0)
    if spells == 0:
        return 0

    # X = greatest MV cast (tracked by APL or estimated from turn/mana)
    max_mv = getattr(gs, '_rootha_max_spell_mv', 0)
    if max_mv == 0:
        # Fallback: estimate from available mana spent
        max_mv = max(1, gs.turn - 1)

    if max_mv <= 0:
        return 0

    # Create X/X blue-red Elemental with flying and haste
    token = Card(f"Elemental Token", "{0}", max_mv, "Token Creature — Elemental",
                 oracle_text="Flying. Haste.")
    token.power = str(max_mv)
    token.toughness = str(max_mv)
    token.turn_entered = gs.turn
    token.summoning_sickness = False  # has haste
    gs.zones.battlefield.append(token)
    gs._log(f"  Rootha combat trigger: {max_mv}/{max_mv} flying haste token")
    return max_mv


def track_spell_mv(gs, spell_mv: int) -> None:
    """Record the MV of a spell cast this turn for Rootha's trigger.

    Call whenever an instant/sorcery is cast.
    """
    current = getattr(gs, '_rootha_max_spell_mv', 0)
    gs._rootha_max_spell_mv = max(current, spell_mv)


def reset_tracking(gs) -> None:
    """Reset per-turn MV tracking at start of turn."""
    gs._rootha_max_spell_mv = 0
