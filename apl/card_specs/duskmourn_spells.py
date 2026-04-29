"""Duskmourn Spells & Utility — 10 cards

Ghost Vacuum {1} Artifact
  {T}: Exile target card from a graveyard.
  {6}{T} Sacrifice: Put all creature cards exiled with it onto battlefield.

Pyroclasm {1}{R} Instant
  Deals 2 damage to each creature.

Exorcise {1}{W} Instant
  Exile target artifact, enchantment, or creature with power 4+.

Get Out {U}{U} Instant
  Counter target creature or enchantment spell. OR Return 1-2 target
  creatures/enchantments to owner's hand.

Nowhere to Run {1}{B} Flash Enchantment
  When ETB: target creature gets -3/-3 until EOT.
  Enchanted creatures can't be sacrificed.

Unable to Scream {U} Enchantment — Aura
  Enchant creature. It loses all abilities, becomes Toy artifact creature
  with base power/toughness 1/1.

Leyline of Resonance {2}{R}{R} Enchantment
  If in opening hand, may begin with it on battlefield.
  Whenever you cast an instant or sorcery, copy it (may choose new targets).

Leyline of the Void {2}{B}{B} Enchantment
  If in opening hand, may begin with it on battlefield.
  If a card would be put into an opponent's GY from anywhere, exile it.

Shardmage's Rescue Enchantment
  {2}, Sacrifice: Scry 1, draw a card.

Turn Inside Out {R} Instant
  Target creature gets +3/+0 until EOT. When it dies this turn, manifest dread.

Decks: Various Standard archetypes.
Spec: apl/card_specs/duskmourn_spells.py
"""
from __future__ import annotations
from data.card import Tag
from engine.match_state import safe_power, safe_toughness

GHOST_VACUUM      = "Ghost Vacuum"
PYROCLASM         = "Pyroclasm"
EXORCISE          = "Exorcise"
GET_OUT           = "Get Out"
NOWHERE_TO_RUN    = "Nowhere to Run"
UNABLE_TO_SCREAM  = "Unable to Scream"
LEYLINE_RESONANCE = "Leyline of Resonance"
LEYLINE_VOID      = "Leyline of the Void"
SHARDMAGE_RESCUE  = "Shardmage's Rescue"
TURN_INSIDE_OUT   = "Turn Inside Out"


def cast(gs, card_name: str, opponent=None) -> bool:
    """Generic cast dispatcher for Duskmourn spell cards.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name != card_name:
            continue
        if not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            continue
        if card_name == PYROCLASM and opponent:
            _pyroclasm(gs, opponent)
        elif card_name == EXORCISE and opponent:
            _exorcise(gs, opponent)
        elif card_name == GET_OUT and opponent:
            _get_out(gs, opponent)
        elif card_name == NOWHERE_TO_RUN and opponent:
            _nowhere_to_run(gs, opponent)
        elif card_name == TURN_INSIDE_OUT:
            _turn_inside_out(gs)
        gs.cast_spell(c)
        return True
    return False


def cast_leyline_if_opening(gs, leyline_name: str) -> bool:
    """Deploy a Leyline from opening hand before turn 1 (free).

    Returns True if deployed.
    """
    for c in list(gs.zones.hand):
        if c.name == leyline_name and gs.turn <= 1:
            gs.zones.hand.remove(c)
            gs.zones.battlefield.append(c)
            c.turn_entered = 0
            gs._log(f"  Leyline: {leyline_name} deployed from opening hand (free)")
            return True
    return False


def is_leyline_active(gs, leyline_name: str) -> bool:
    """True if the Leyline is on the battlefield."""
    return any(c.name == leyline_name for c in gs.zones.battlefield)


def _pyroclasm(gs, opponent):
    """Pyroclasm: 2 damage to each creature."""
    killed = []
    for owner in (gs, opponent):
        for cr in list(owner.zones.battlefield):
            if cr.has(Tag.CREATURE) and not cr.is_land():
                if safe_toughness(cr) <= 2:
                    killed.append((cr, owner))
    for cr, owner in killed:
        if cr in owner.zones.battlefield:
            owner.zones.battlefield.remove(cr)
            owner.zones.graveyard.append(cr)
    gs._log(f"  Pyroclasm: 2 damage to each creature, killed {len(killed)}")


def _exorcise(gs, opponent):
    """Exorcise: exile artifact, enchantment, or creature with power 4+."""
    targets = [c for c in opponent.zones.battlefield
               if not c.is_land() and (
                   c.has(Tag.ARTIFACT) or c.has(Tag.ENCHANTMENT)
                   or (c.has(Tag.CREATURE) and safe_power(c) >= 4))]
    if targets:
        target = max(targets, key=lambda c: safe_power(c))
        opponent.zones.battlefield.remove(target)
        opponent.zones.exile.append(target)
        gs._log(f"  Exorcise: exile {target.name}")


def _get_out(gs, opponent):
    """Get Out: counter OR bounce 1-2 creatures/enchantments."""
    # Bounce the best 1-2 opponent permanents
    targets = sorted([c for c in opponent.zones.battlefield
                      if not c.is_land() and (c.has(Tag.CREATURE) or c.has(Tag.ENCHANTMENT))],
                     key=lambda c: -getattr(c, 'cmc', 0))[:2]
    for t in targets:
        opponent.zones.battlefield.remove(t)
        opponent.zones.hand.append(t)
    gs._log(f"  Get Out: bounce {[t.name for t in targets]}")


def _nowhere_to_run(gs, opponent):
    """-3/-3 to opponent's biggest creature."""
    critters = [c for c in opponent.zones.battlefield
                if c.has(Tag.CREATURE) and not c.is_land()]
    if critters:
        t = max(critters, key=lambda c: safe_power(c))
        # Apply -3/-3 until EOT (track with counters)
        t.counters = getattr(t, 'counters', 0) - 3
        gs._log(f"  Nowhere to Run: {t.name} gets -3/-3")


def _turn_inside_out(gs):
    """Turn Inside Out: target creature gets +3/+0 until EOT."""
    critters = [c for c in gs.zones.battlefield
                if c.has(Tag.CREATURE) and not c.is_land()]
    if critters:
        target = max(critters, key=lambda c: safe_power(c))
        target.counters = getattr(target, 'counters', 0) + 3
        gs._log(f"  Turn Inside Out: {target.name} gets +3/+0 until EOT")
