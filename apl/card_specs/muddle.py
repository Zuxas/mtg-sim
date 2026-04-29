"""Muddle, the Ever-Changing — {2}{U}{R} 3/3 Legendary Creature — Elemental Otter Shapeshifter

Oracle:
  Whenever you cast an instant or sorcery spell, Muddle becomes a copy of
  up to one target nonlegendary creature you control until end of turn,
  except it has myriad. (Whenever it attacks, for each opponent other
  than defending player, you may create a token copy that's tapped and
  attacking that player or a planeswalker they control. Exile tokens at
  end of combat.)

Decks: Izzet Cauldron, Standard Izzet combo.

Key decisions:
- Cast T4 (2UR). 3/3 base.
- On every instant/sorcery: becomes a copy of your best nonlegendary
  creature + gains myriad (creates attack copies vs other opponents).
- In 1v1 Standard sim: myriad has no effect (only 1 opponent).
  Main value: copy your best creature (e.g. 7/7 Prismari body).
- Best copy target: largest creature on board (Dawning Archaic, Rootha)
- Multiple spells per turn: Muddle copies the last target chosen.
- Combat: attack as the copied creature; myriad tokens are exiled EOC.

Spec: apl/card_specs/muddle.py
"""
from __future__ import annotations
from data.card import Tag
from engine.match_state import safe_power

NAME = "Muddle, the Ever-Changing"
CMC = 4  # {2}{U}{R}


def cast(gs, opponent=None) -> bool:
    """Cast Muddle T4. Strong enabler once spells are flowing.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            gs._log(f"  Muddle: 3/3, copies best creature + myriad on each spell cast")
            return True
    return False


def is_active(gs) -> bool:
    """True if Muddle is on the battlefield."""
    return any(c.name == NAME for c in gs.zones.battlefield)


def apply_copy_trigger(gs) -> str:
    """When an instant/sorcery is cast, Muddle becomes the best creature.

    Finds the best nonlegendary creature on the battlefield and updates
    Muddle's power/toughness to match (simplified: updates the stat
    on the card object).

    Returns name of the copied creature, or '' if no target.
    """
    if not is_active(gs):
        return ''

    muddle = next((c for c in gs.zones.battlefield if c.name == NAME), None)
    if not muddle:
        return ''

    # Find best nonlegendary creature (highest power)
    candidates = [c for c in gs.zones.battlefield
                  if c.has(Tag.CREATURE) and not c.is_land()
                  and 'Legendary' not in (getattr(c, 'type_line', '') or '')
                  and c is not muddle]

    if not candidates:
        return ''

    best = max(candidates, key=lambda c: safe_power(c))
    # Update Muddle's stats to match (copy until EOT)
    muddle.power = best.power
    muddle.toughness = best.toughness
    muddle._copied_name = best.name
    gs._log(f"  Muddle copies {best.name} ({safe_power(best)}/{best.toughness}) + myriad")
    return best.name


def current_power(gs) -> int:
    """Current power of Muddle (may be updated by copy trigger)."""
    for c in gs.zones.battlefield:
        if c.name == NAME:
            return safe_power(c)
    return 0
