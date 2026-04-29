"""Magma Opus — {6}{U}{R} Instant

Oracle:
  Magma Opus deals 4 damage divided as you choose among any number of
  targets. Tap two target permanents. Draw two cards. Create a 4/4 blue
  and red Elemental creature token.
  Discard Magma Opus: Create a Treasure token. Activate only as a sorcery.

Decks: Izzet Cauldron (primary finisher), any Standard Izzet.

Key decisions:
- Cast at {6}{U}{R} = 8 mana. Typically T7-8 naturally, or miracle {2}
  with Lorehold, or free with Zaffai, or Rootha combat trigger (huge token).
- Effect: 4 damage + tap 2 permanents + draw 2 + 4/4 token = game-winning.
- Discard mode: turn Magma Opus into a Treasure for mana acceleration.
  Use on T3-4 to ramp toward casting it properly later.
- With Prismari (storm): storm copies = 4 damage × copies. Two storm copies
  with 2 prior spells = 12 damage + 3 tokens + 6 draws.
- With Rootha: Magma Opus (MV 8) → 8/8 flying haste token.
- Priority: cast it for free when possible (Zaffai, Lorehold miracle).
  If casting normally, only at 8+ mana.

Spec: apl/card_specs/magma_opus.py
"""
from __future__ import annotations
from data.card import Card, Tag
from engine.match_state import safe_power

NAME = "Magma Opus"
CMC = 8   # {6}{U}{R}
DAMAGE = 4
DISCARD_FOR_TREASURE = True


def cast(gs, opponent=None) -> bool:
    """Cast Magma Opus at full cost. Only when 8+ mana available.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            _apply_effect(gs, opponent)
            return True
    return False


def cast_free(gs, opponent=None) -> bool:
    """Cast Magma Opus for free (Zaffai, Lorehold miracle, etc).

    Removes from hand, applies full effect.
    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME:
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            _apply_effect(gs, opponent)
            gs._log(f"  Magma Opus (free cast): 4 damage + tap 2 + draw 2 + 4/4")
            return True
    return False


def discard_for_treasure(gs) -> bool:
    """Discard Magma Opus to create a Treasure token (mana ramp).

    Use when you need early mana but have Magma Opus stuck in hand.
    Returns True if discarded.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME:
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            gs._log(f"  Magma Opus discarded: +1 Treasure (mana ramp)")
            return True
    return False


def _apply_effect(gs, opponent):
    """Apply Magma Opus resolution: 4 damage, tap 2, draw 2, 4/4 token."""
    # 4 damage to opponent face (simplified: deal all to face)
    gs.damage_dealt += DAMAGE
    if opponent:
        pass  # damage goes to opponent
    gs._log(f"  Magma Opus: {DAMAGE} damage ({gs.damage_dealt} total)")

    # Tap 2 opponent permanents (remove their blockers effectively)
    if opponent:
        untapped = [c for c in opponent.zones.battlefield
                    if not c.is_land() and not getattr(c, 'tapped', False)][:2]
        for c in untapped:
            c.tapped = True
        if untapped:
            gs._log(f"  Magma Opus: tap {[c.name for c in untapped]}")

    # Draw 2 cards
    gs.zones.draw(2)
    gs._log(f"  Magma Opus: draw 2")

    # Create 4/4 Elemental token
    token = Card("Elemental Token", "{0}", 4, "Token Creature — Elemental")
    token.power = "4"
    token.toughness = "4"
    token.turn_entered = gs.turn
    token.summoning_sickness = True
    gs.zones.battlefield.append(token)
    gs._log(f"  Magma Opus: 4/4 Elemental token created")
