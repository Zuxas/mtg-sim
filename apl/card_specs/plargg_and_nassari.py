"""Plargg and Nassari — {3}{R}{R} 5/4 Legendary Creature

Oracle:
  At the beginning of your upkeep, each player exiles cards from the top
  of their library until they exile a nonland card. Each player may cast
  the exiled nonland card without paying its mana cost. Put the other
  exiled cards on the bottom of that player's library in a random order.

Decks: Izzet Cauldron, any Standard red value engine.

Key decisions:
- Cast T5 (3RR). 5/4 body.
- Upkeep trigger: both players exile and get a free spell.
  We get their top nonland free; they get ours free.
  Asymmetry: more valuable when our library has high-CMC spells (Magma
  Opus, Mathemagics) vs their lower-CMC spells.
- With Rootha/Prismari: the free spell from Plargg counts as a spell
  cast, triggering storm/magecraft/cascade.
- Risk: opponent also gets a free spell. Mitigated if their top card is
  a land (they keep exiling) or low-CMC.
- Best in decks with many high-CMC instants/sorceries near top of library
  (draw-heavy/cantrip-heavy to stack library).

Spec: apl/card_specs/plargg_and_nassari.py
"""
from __future__ import annotations
from data.card import Tag

NAME = "Plargg and Nassari"
CMC = 5  # {3}{R}{R}


def cast(gs, opponent=None) -> bool:
    """Cast Plargg and Nassari T5. Starts generating free spells each upkeep.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            gs._log(f"  Plargg and Nassari: 5/4, upkeep free nonland spell from library")
            return True
    return False


def is_active(gs) -> bool:
    """True if Plargg and Nassari is on the battlefield."""
    return any(c.name == NAME for c in gs.zones.battlefield)


def fire_upkeep_trigger(gs, opponent=None) -> bool:
    """At beginning of upkeep, exile until nonland for both players.

    We cast our exiled nonland for free. Opponent casts theirs for free.
    Returns True if we got a free spell.
    """
    if not is_active(gs):
        return False

    # Find our top nonland card
    our_spell = None
    our_bottomed = []
    for card in list(gs.zones.library):
        if not card.is_land():
            our_spell = card
            gs.zones.library.remove(card)
            break
        our_bottomed.append(card)
        gs.zones.library.remove(card)
    gs.zones.library.extend(our_bottomed)  # put lands on bottom

    if not our_spell:
        return False

    # Cast for free
    spell_cmc = getattr(our_spell, 'cmc', 0)
    if our_spell.has(Tag.CREATURE):
        gs.zones.battlefield.append(our_spell)
        our_spell.turn_entered = gs.turn
        our_spell.summoning_sickness = True
    else:
        gs.zones.graveyard.append(our_spell)

    gs._log(f"  Plargg upkeep: free cast {our_spell.name} (CMC {spell_cmc})")
    return True
