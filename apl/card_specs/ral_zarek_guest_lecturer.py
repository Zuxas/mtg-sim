"""Ral Zarek, Guest Lecturer — {1}{B}{B} Planeswalker — Ral (starts at 4 loyalty)

Oracle:
  +1: Surveil 2.
  −1: Any number of target players each discard a card.
  −2: Return target creature or planeswalker card from your graveyard to
      your hand.

Decks: Jeskai Control (splash black?), Dimir midrange, Grixis builds.

Key decisions:
- Cast T4 (1BB). 4 starting loyalty.
- +1 (surveil 2): filter your top 2 cards, put unwanted in GY. Use when
  you want to find specific cards or fuel Dawning Archaic GY count.
- −1 (discard target player): strip opponent's best card from hand.
  Repeat with +1/−1 cycle: +1 loyalty, then −1 to discard again.
- −2 (return creature/PW from GY): recur Prismari, Silverquill, Deekah.
  Most powerful when a key threat dies early.
- Loyalty management: +1 twice → 6 loyalty → −2 to recur. Or +1/−1
  cycle for repeated hand disruption.
- Protect with other permanents; Ral doesn't have protection abilities.

Spec: apl/card_specs/ral_zarek_guest_lecturer.py
"""
from __future__ import annotations
from data.card import Tag
from engine.match_state import safe_power

NAME = "Ral Zarek, Guest Lecturer"
CMC = 3   # {1}{B}{B}
START_LOYALTY = 4

KEY_CREATURES_TO_RECUR = {
    "Prismari, the Inspiration",
    "Silverquill, the Disputant",
    "Deekah, Fractal Theorist",
    "Veyran, Voice of Duality",
    "The Dawning Archaic",
}


def cast(gs, opponent=None) -> bool:
    """Cast Ral T4 (1BB). Start with +1 to surveil and build loyalty.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            # Place Ral as a permanent with loyalty counters
            c.counters = START_LOYALTY
            gs._log(f"  Ral Zarek Guest Lecturer: PW with {START_LOYALTY} loyalty")
            # Immediately +1 to surveil
            activate_plus1(gs)
            return True
    return False


def is_active(gs) -> bool:
    """True if Ral is on the battlefield."""
    return any(c.name == NAME and 'Planeswalker' in (getattr(c,'type_line','') or '')
               for c in gs.zones.battlefield)


def activate_plus1(gs) -> bool:
    """Ral +1: Surveil 2 (look at top 2, keep/GY as desired)."""
    ral = next((c for c in gs.zones.battlefield if c.name == NAME), None)
    if not ral:
        return False
    ral.counters = getattr(ral, 'counters', START_LOYALTY) + 1
    # Surveil 2: put non-useful cards in GY (keep creatures/key spells on top)
    surveilled = []
    for _ in range(min(2, len(gs.zones.library))):
        card = gs.zones.library.pop(0)
        if card.is_land() or (not card.has(Tag.CREATURE) and getattr(card,'cmc',0) <= 1):
            gs.zones.graveyard.append(card)  # put in GY
            surveilled.append(f"{card.name}→GY")
        else:
            gs.zones.library.insert(0, card)  # keep on top
            surveilled.append(f"{card.name}→top")
    gs._log(f"  Ral +1 surveil 2: {surveilled} (loyalty {ral.counters})")
    return True


def activate_minus1(gs, opponent=None) -> bool:
    """Ral −1: Target player discards a card. Use on opponent."""
    ral = next((c for c in gs.zones.battlefield if c.name == NAME), None)
    if not ral or getattr(ral, 'counters', 0) < 1:
        return False
    ral.counters -= 1
    if opponent and opponent.zones.hand:
        # Discard opponent's highest-CMC card
        discard_target = max(opponent.zones.hand, key=lambda c: getattr(c,'cmc',0))
        opponent.zones.hand.remove(discard_target)
        opponent.zones.graveyard.append(discard_target)
        gs._log(f"  Ral −1: opponent discards {discard_target.name} "
                f"(loyalty {ral.counters})")
    return True


def activate_minus2(gs, opponent=None) -> bool:
    """Ral −2: Return best key creature/PW from GY to hand."""
    ral = next((c for c in gs.zones.battlefield if c.name == NAME), None)
    if not ral or getattr(ral, 'counters', 0) < 2:
        return False

    # Find best target in GY
    gy_targets = [c for c in gs.zones.graveyard
                  if c.has(Tag.CREATURE) or 'Planeswalker' in (getattr(c,'type_line','') or '')]
    if not gy_targets:
        return False

    # Prefer key engine pieces
    key = next((c for c in gy_targets if c.name in KEY_CREATURES_TO_RECUR), None)
    target = key if key else max(gy_targets, key=lambda c: getattr(c,'cmc',0))

    ral.counters -= 2
    gs.zones.graveyard.remove(target)
    gs.zones.hand.append(target)
    gs._log(f"  Ral −2: return {target.name} from GY to hand "
            f"(loyalty {ral.counters})")
    return True
