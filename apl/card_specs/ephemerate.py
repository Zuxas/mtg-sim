"""Ephemerate — `{W}` instant, blink + rebound.

Oracle:
  Exile target creature you control, then return it to the battlefield
  under its owner's control. Rebound (if cast from hand, exile it; you
  may cast it from exile during your next upkeep without paying mana).

Decks using this spec: Jeskai Blink, UW Blink, Esper Blink.

Reference impl: apl/jeskai_blink_match.py:298-306 + 394-425 (blink_best_etb
                + rebound flag); apl/uw_blink_match.py similar.

Spec: harness/specs/2026-04-29-card-specs-framework.md
"""
from __future__ import annotations

NAME = "Ephemerate"
CAST_CMC = 1


def cast(gs, opponent=None, target_picker=None, rebound_flag_setter=None) -> bool:
    """Cast Ephemerate to blink best ETB creature on battlefield.

    Args:
      gs: GameState
      opponent: opponent state (None for goldfish)
      target_picker: callable(etb_list) -> Card or None. If None, uses default
                     goldfish priority.
      rebound_flag_setter: callable() -> None. Called after Ephemerate enters
                          exile (rebound). APL should set its own
                          self._ephemerate_rebound = True so next upkeep
                          re-fires the blink for free.

    Returns True if cast.
    """
    from data.card import Tag

    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            # Find ETB creatures on battlefield
            etb_creatures = _etb_targets_on_board(gs)
            if not etb_creatures:
                return False  # no value in casting

            target = (target_picker(etb_creatures) if target_picker
                      else _default_etb_priority(etb_creatures))
            if not target:
                return False

            # Pay mana, move Ephemerate to exile (rebound)
            gs.mana_pool.pay(c.mana_cost, c.cmc)
            gs.zones.hand.remove(c)
            gs.zones.exile.append(c)

            # Trigger ETB on target by dispatching to its card_spec
            _retrigger_etb(gs, target, opponent=opponent)

            if rebound_flag_setter:
                rebound_flag_setter()
            gs._log(f"  Ephemerate: blink {target.name} (rebound next upkeep)")
            return True
    return False


def _etb_targets_on_board(gs) -> list:
    """Return list of ETB creatures on our battlefield worth blinking."""
    from data.card import Tag
    GOLDFISH_VIABLE = {
        "Phlage, Titan of Fire's Fury",
        "Quantum Riddler",
        "Casey Jones, Vigilante",
    }
    return [c for c in gs.zones.battlefield
            if c.has(Tag.CREATURE) and not c.is_land()
            and c.name in GOLDFISH_VIABLE]


def _default_etb_priority(etb_creatures: list):
    """Default priority: Phlage > Quantum > Casey."""
    priority_order = (
        "Phlage, Titan of Fire's Fury",
        "Quantum Riddler",
        "Casey Jones, Vigilante",
    )
    for name in priority_order:
        for c in etb_creatures:
            if c.name == name:
                return c
    return None


def _retrigger_etb(gs, card, opponent=None) -> None:
    """Re-fire the ETB effect of `card` (called by blink mechanism)."""
    if card.name == "Phlage, Titan of Fire's Fury":
        # 3 face dmg + 3 life (then sacrifice — but blink leaves it on field)
        # NOTE: Ephemerate-blink-Phlage interaction: the sacrifice trigger
        # does NOT fire on the blink because the sacrifice is part of Phlage's
        # ETB clause, which IS what we're re-triggering. So Phlage actually
        # SACRIFICES AGAIN after the blink-ETB. Net: 3+3 dmg + 6 life, but
        # Phlage ends up in GY again. (Same as casting twice = same effect.)
        gs.damage_dealt += 3
        gs.life += 3
        # Move from BF to GY (sacrifice clause re-fires)
        if card in gs.zones.battlefield:
            gs.zones.battlefield.remove(card)
            gs.zones.graveyard.append(card)
        gs._log(f"    Blink-ETB Phlage: 3 dmg + 3 life (sac re-fired)")
    elif card.name == "Quantum Riddler":
        gs.zones.draw(1)
        gs._log(f"    Blink-ETB Quantum Riddler: draw 1")
    elif card.name == "Casey Jones, Vigilante":
        gs.zones.draw(3)
        gs._log(f"    Blink-ETB Casey Jones: draw 3")
        # Note: discard-3-next-upkeep flag is the APL's responsibility to track


def fire_rebound(gs, opponent=None, target_picker=None) -> bool:
    """Fire the rebound: cast Ephemerate from exile for free.

    Called by APLs at upkeep when their ephemerate_rebound flag is set.
    Returns True if rebound fired.
    """
    # Find Ephemerate in exile
    eph_in_exile = [c for c in gs.zones.exile if c.name == NAME]
    if not eph_in_exile:
        return False

    etb_creatures = _etb_targets_on_board(gs)
    if not etb_creatures:
        # Move Ephemerate to GY (rebound consumed without effect)
        gs.zones.exile.remove(eph_in_exile[0])
        gs.zones.graveyard.append(eph_in_exile[0])
        return False

    target = (target_picker(etb_creatures) if target_picker
              else _default_etb_priority(etb_creatures))
    if not target:
        return False

    eph = eph_in_exile[0]
    gs.zones.exile.remove(eph)
    gs.zones.graveyard.append(eph)  # rebound resolution -> GY
    _retrigger_etb(gs, target, opponent=opponent)
    gs._log(f"  Ephemerate REBOUND: free blink {target.name}")
    return True
