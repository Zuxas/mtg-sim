"""Maelstrom Artisan — {1}{R}{R} 3/2 Creature — Human Wizard

Oracle:
  Haste
  This creature enters prepared. (While it's prepared, you may cast a copy
  of its spell. Doing so unprepares it.)

Note: Like Emeritus of Conflict, "its spell" = the back face (Rocket Volley
or similar). Enters ALREADY prepared, so you get the free spell immediately
on cast — unlike Emeritus which requires casting a 3rd spell to become prepared.
Haste = attacks the same turn it's cast.

Decks: Izzet Cauldron, any red spells deck.

Key decisions:
- Cast T3 (1RR). 3/2 haste attacks same turn.
- Enters prepared: immediate free back-face spell (Rocket Volley = deal damage?).
- Use prepared spell for face damage or to remove a blocker.
- Best on T3: cast + attack 3 + use prepared spell.
- Second copy: each Artisan enters prepared independently.

Spec: apl/card_specs/maelstrom_artisan.py
"""
from __future__ import annotations
from engine.card_db import get_oracle

NAME = "Maelstrom Artisan"
CMC = 3  # {1}{R}{R}
BACK_FACE = "Rocket Volley"
PREPARED_DAMAGE = 3  # Rocket Volley approximation


def cast(gs, opponent=None) -> bool:
    """Cast Maelstrom Artisan T3. Enters prepared → use free spell immediately.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            # Mark as prepared
            c._prepared = True
            gs._log(f"  Maelstrom Artisan: 3/2 haste, enters prepared (free {BACK_FACE})")
            # Use prepared spell immediately
            use_prepared_spell(gs, c, opponent)
            return True
    return False


def use_prepared_spell(gs, artisan, opponent=None) -> bool:
    """Cast the prepared spell (back face) for free.

    Returns True if the spell was cast.
    """
    if not getattr(artisan, '_prepared', False):
        return False
    artisan._prepared = False  # unprepare
    # Cast Rocket Volley (approximated as 3 damage)
    gs.damage_dealt += PREPARED_DAMAGE
    gs._log(f"  Artisan prepared: {BACK_FACE} = {PREPARED_DAMAGE} damage "
            f"({gs.damage_dealt} total)")
    return True


def check_and_fire_prepared(gs, opponent=None) -> bool:
    """Check all Artisans on board and fire any prepared ones.

    Returns True if any prepared spell fired.
    """
    fired = False
    for c in gs.zones.battlefield:
        if c.name == NAME and getattr(c, '_prepared', False):
            fired = use_prepared_spell(gs, c, opponent) or fired
    return fired
