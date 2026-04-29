"""Ozolith, the Shattered Spire — {1}{G} Legendary Artifact

Oracle:
  If one or more +1/+1 counters would be put on an artifact or creature
  you control, that many plus one +1/+1 counters are put on it instead.
  {1}{G}, {T}: Put a +1/+1 counter on target artifact or creature you
  control. Activate only as a sorcery.
  Cycling {W/G} ({W/G}, Discard this card: Draw a card.)

Decks: Simic Ouroboroid, any counter-based Standard deck.

Key decisions:
- Cast T2 (1G). Passive counter amplifier.
- Passive: every +1/+1 counter placed = 1 extra counter.
  e.g. Zimone Infinite Analyst places 1 counter from X-spell = gets 2.
  e.g. Deekah Fractal token gets X counters = gets X+1 counters.
  e.g. Striding Shotcaller prepared trigger = 2 counters instead of 1.
- Activated: {1}{G} tap, add 1 counter to any artifact/creature.
  (With Ozolith, it places 2 instead of 1.)
- Cycling: discard for {W/G} to draw a card if not needed.
- Key synergy: Nev (trample for countered creatures) + Ozolith = faster
  counter buildup → tramplers attacking sooner.

Spec: apl/card_specs/ozolith.py
"""
from __future__ import annotations
from data.card import Tag
from engine.match_state import safe_power

NAME = "Ozolith, the Shattered Spire"
CMC = 2  # {1}{G}


def cast(gs, opponent=None) -> bool:
    """Cast Ozolith T2. Passive counter amplifier takes effect immediately.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            gs._log(f"  Ozolith: +1/+1 counters amplified (+1 per counter placed)")
            return True
    return False


def is_active(gs) -> bool:
    """True if Ozolith is on the battlefield."""
    return any(c.name == NAME for c in gs.zones.battlefield)


def amplify_counters(counters_being_placed: int) -> int:
    """Return the amplified counter count (N+1 instead of N)."""
    return counters_being_placed + 1


def activate(gs, target=None) -> bool:
    """Activated ability: {1}{G} tap, put 1+1=2 counters on a creature.

    Returns True if activated.
    """
    if not is_active(gs):
        return False
    ozolith = next((c for c in gs.zones.battlefield if c.name == NAME), None)
    if not ozolith or getattr(ozolith, 'tapped', False):
        return False
    if gs.mana_pool.total() < 2:
        return False

    # Find best target (creature with most benefit from 2 extra counters)
    if target is None:
        candidates = [c for c in gs.zones.battlefield
                      if c.has(Tag.CREATURE) and not c.is_land()]
        if not candidates:
            return False
        target = max(candidates, key=lambda c: safe_power(c))

    try:
        gs.mana_pool.pay("{1}{G}", 2)
    except Exception:
        return False

    ozolith.tapped = True
    # With Ozolith: placing 1 counter = 2 counters (amplified)
    counters = amplify_counters(1)
    target.counters = getattr(target, 'counters', 0) + counters
    gs._log(f"  Ozolith activated: +{counters} counters on {target.name}")
    return True
