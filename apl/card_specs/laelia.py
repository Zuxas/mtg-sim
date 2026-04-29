"""Laelia, the Blade Reforged — {2}{R} 2/2 Legendary Creature — Spirit Warrior

Oracle:
  Haste
  Whenever Laelia attacks, exile the top card of your library. You may
  play that card this turn.
  Whenever one or more cards are put into exile from your library or
  graveyard, put a +1/+1 counter on Laelia.

Decks: Izzet Cauldron, any aggressive red deck.

Key decisions:
- Cast T3 (2R). 2/2 haste attacks same turn.
- Attack trigger: exile top card, may play it (land play OR cast spell).
  Grows by +1/+1 each exile trigger.
- With Plargg: upkeep exile + attack exile = 2 counters per turn.
  Laelia quickly becomes 4/4, 5/5, 6/6.
- With Prismari: casting exiled spells triggers storm → more spells →
  more exiles → more counters.
- With Advanced Reconstruction: mill = exile = counters.
- Haste = T3 attack for 2, T4 attack for 3 if one counter landed.
- Key: play the exiled card even if it's a land (free land drop is fine).

Spec: apl/card_specs/laelia.py
"""
from __future__ import annotations
from data.card import Tag

NAME = "Laelia, the Blade Reforged"
CMC = 3   # {2}{R}


def cast(gs, opponent=None) -> bool:
    """Cast Laelia T3. Haste means attack immediately.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            gs._log(f"  Laelia: 2/2 haste, attack exile + counter engine")
            return True
    return False


def is_active(gs) -> bool:
    """True if Laelia is on the battlefield."""
    return any(c.name == NAME for c in gs.zones.battlefield)


def fire_attack_trigger(gs, opponent=None) -> bool:
    """When Laelia attacks, exile top library card and (may) play it.

    Also puts +1/+1 counter on Laelia (cards exiled from library).
    Returns True if triggered.
    """
    if not is_active(gs):
        return False
    if not gs.zones.library:
        return False

    laelia = next(c for c in gs.zones.battlefield if c.name == NAME)

    # Exile top card
    exiled = gs.zones.library.pop(0)
    gs.zones.exile.append(exiled)

    # +1/+1 counter for the exile
    laelia.counters = getattr(laelia, 'counters', 0) + 1
    power = 2 + laelia.counters
    laelia.power = str(power)
    laelia.toughness = str(power)

    # Play the exiled card this turn
    played = False
    if exiled.is_land() and not gs.land_played:
        gs.zones.exile.remove(exiled)
        gs.zones.battlefield.append(exiled)
        gs.land_played = True
        played = True
        gs._log(f"  Laelia attack: exile+play land {exiled.name}, "
                f"Laelia now {power}/{power}")
    elif not exiled.is_land() and gs.mana_pool.can_cast(exiled.mana_cost, exiled.cmc):
        gs.zones.exile.remove(exiled)
        if exiled.has(Tag.CREATURE):
            gs.zones.battlefield.append(exiled)
            exiled.turn_entered = gs.turn
            exiled.summoning_sickness = True
        else:
            gs.zones.graveyard.append(exiled)
        played = True
        gs._log(f"  Laelia attack: exile+cast {exiled.name} (CMC {getattr(exiled,'cmc',0)}), "
                f"Laelia now {power}/{power}")
    else:
        gs._log(f"  Laelia attack: exile {exiled.name} (can't play), "
                f"Laelia now {power}/{power}")

    return True


def current_power(gs) -> int:
    """Current power of Laelia including +1/+1 counters."""
    laelia = next((c for c in gs.zones.battlefield if c.name == NAME), None)
    if not laelia:
        return 0
    return 2 + getattr(laelia, 'counters', 0)
