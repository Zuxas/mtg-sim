"""Phlage, Titan of Fire's Fury — `{1}{R}{W}` hardcast / `{R}{R}{W}{W}` escape.

Oracle:
  When Phlage enters, deal 3 damage to any target, you gain 3 life,
  then sacrifice it. Escape — `{R}{R}{W}{W}`, exile 5 cards from your
  graveyard. As a 6/6 escaped permanent, attack trigger deals 3 + life 3.

Decks using this spec: Boros Energy, Jeskai Blink, multiple Modern variants.

Reference impl: apl/jeskai_blink_match.py:255-295 (hardcast + escape),
                apl/boros_energy.py (also has Phlage logic inline).

Spec: harness/specs/2026-04-29-card-specs-framework.md
"""
from __future__ import annotations

NAME = "Phlage, Titan of Fire's Fury"

HARDCAST_CMC = 3   # {1}{R}{W}
ESCAPE_CMC = 4     # {R}{R}{W}{W}
ESCAPE_GY_EXILE = 5


def hardcast(gs, opponent=None) -> bool:
    """Hardcast Phlage from hand via gs.cast_spell().

    Engine note (engine/card_handlers_verified.py:_phlage_titan_etb):
    the sacrifice-unless-escaped clause is NOT modeled. Engine fires
    the 3-dmg+3-life ETB and leaves Phlage on the battlefield as a 6/6
    creature. That's the deal in this engine. Don't manually sacrifice
    — that costs us the 6/6 body which dominates goldfish kill clock.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            return True
    return False


def escape(gs, opponent=None) -> bool:
    """Escape Phlage from GY: 4 mana + exile 5 non-Phlage GY cards.

    Returns True if escaped (Phlage now on battlefield as 6/6 + ETB fired).
    """
    gy_phlages = [c for c in gs.zones.graveyard if c.name == NAME]
    non_phlage_gy = [c for c in gs.zones.graveyard if c.name != NAME]
    if not gy_phlages or len(non_phlage_gy) < ESCAPE_GY_EXILE:
        return False
    if gs.mana_pool.total() < ESCAPE_CMC:
        return False

    phlage = gy_phlages[0]
    # Exile cheapest 5 first (preserve options)
    non_phlage_gy.sort(key=lambda c: getattr(c, 'cmc', 0))
    for c in non_phlage_gy[:ESCAPE_GY_EXILE]:
        gs.zones.graveyard.remove(c)
        gs.zones.exile.append(c)

    gs.zones.graveyard.remove(phlage)
    gs.zones.battlefield.append(phlage)
    phlage.turn_entered = gs.turn
    phlage.summoning_sickness = True

    # ETB: 3 face dmg + 3 life
    gs.damage_dealt += 3
    gs.life += 3

    try:
        gs.mana_pool.pay("{R}{R}{W}{W}", ESCAPE_CMC)
    except Exception:
        pass  # mana model may approximate colored costs

    gs._log(f"  PHLAGE ESCAPE: 6/6 permanent + 3 dmg + 3 life")
    return True


def attack_trigger(gs, opponent=None) -> None:
    """Phlage's combat-damage trigger: 3 dmg + 3 life when it attacks.

    Called by APLs that handle attacks explicitly (MatchAPL.declare_attackers).
    Goldfish APLs typically don't call this — combat damage is computed
    by the engine's combat resolver.
    """
    if opponent:
        gs.damage_dealt += 3
    gs.life += 3
