"""Solitude — `{3}{W}` 3/2 flash flier, Evoke by exiling a white card.

Oracle:
  Flash. Flying. When Solitude enters, exile up to one target creature an
  opponent controls until Solitude leaves the battlefield. That creature's
  controller gains life equal to its power. Evoke — Exile a white card from
  your hand (you may cast this spell for its evoke cost; if you do, sacrifice
  it when it enters).

Decks using this spec: Esper Blink, UW Blink, multiple Modern white blink
shells.

Reference impl: apl/esper_blink_match.py:160-182 (_try_solitude_pitch +
                ETB exile) and the SOLITUDE constant / pitch block ~line 96;
                apl/uw_blink_match.py similar.

GOLDFISH-AWARENESS: evoke and the ETB exile are DEAD with opponent=None
(there is nothing on an opponent's board to exile). Both `cast()` and
`evoke()` early-return False when opponent is None — Solitude does nothing
in goldfish (mirrors ragavan.dash's `if opponent is None: return False`
guard). This is why the source spec excluded Solitude from the goldfish POC.

Spec: harness/specs/2026-04-29-card-specs-framework.md
"""
from __future__ import annotations

NAME = "Solitude"
HARDCAST_CMC = 4   # {3}{W}


def _safe_power(card) -> int:
    """Power as int, tolerating None / '*' (mirrors esper_blink_match.safe_power)."""
    try:
        return int(getattr(card, "power", 0) or 0)
    except (ValueError, TypeError):
        return 0


def best_exile_target(gs, opponent=None):
    """Pick the biggest opponent creature worth exiling (>=3 power).

    Returns the creature or None (no opponent, empty board, or nothing big
    enough to be worth the card). Mirrors esper_blink_match._try_solitude_pitch
    targeting (max power, threshold 3).
    """
    if opponent is None:
        return None
    from data.card import Tag
    opp_creatures = [c for c in opponent.zones.battlefield
                     if not c.is_land() and c.has(Tag.CREATURE)]
    if not opp_creatures:
        return None
    target = max(opp_creatures, key=_safe_power)
    if _safe_power(target) < 3:
        return None
    return target


def _etb_exile(gs, opponent, target) -> None:
    """Solitude ETB: exile target opp creature; its controller gains life
    equal to its power (oracle: 'That creature's controller gains life...')."""
    if target in opponent.zones.battlefield:
        opponent.zones.battlefield.remove(target)
        opponent.zones.exile.append(target)
    opponent.life += _safe_power(target)


def cast(gs, opponent=None) -> bool:
    """Hardcast Solitude ({3}{W}) as a 3/2 flash flier + ETB exile.

    Goldfish-dead: the only modeled value is the ETB exile, which needs an
    opponent. Per spec, Solitude does NOTHING in goldfish, so this returns
    False when opponent is None.

    Returns True if cast.
    """
    if opponent is None:
        return False  # goldfish-skip: nothing to exile, do nothing
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            target = best_exile_target(gs, opponent)
            if target is not None:
                _etb_exile(gs, opponent, target)
                gs._log(f"  Solitude (hardcast) exile {target.name}")
            return True
    return False


def evoke(gs, opponent=None) -> bool:
    """Evoke Solitude: pitch a white card from hand for free removal.

    Exiles a white card from hand, puts Solitude onto the battlefield (it is
    sacrificed by the evoke clause, but the engine/reference impl leaves it on
    battlefield as the body until the next state check; we mirror the
    reference's place-on-battlefield behavior), and exile-removes the
    opponent's biggest threat via the ETB.

    Goldfish-dead: returns False when opponent is None (nothing to exile).

    Returns True if evoked.
    """
    if opponent is None:
        return False  # goldfish-skip
    target = best_exile_target(gs, opponent)
    if target is None:
        return False
    solitude = next((c for c in gs.zones.hand if c.name == NAME), None)
    if solitude is None:
        return False
    from data.card import Tag
    white_cards = [c for c in gs.zones.hand
                   if c is not solitude and 'W' in (getattr(c, 'mana_cost', '') or '')]
    if not white_cards:
        return False
    pitch = min(white_cards,
                key=lambda c: _safe_power(c) if c.has(Tag.CREATURE) else 0)
    gs.zones.hand.remove(solitude)
    gs.zones.hand.remove(pitch)
    gs.zones.exile.append(pitch)
    gs.zones.battlefield.append(solitude)
    solitude.turn_entered = gs.turn
    solitude.summoning_sickness = True
    _etb_exile(gs, opponent, target)
    gs._log(f"  Solitude (evoke, pitch {pitch.name}) exile {target.name}")
    return True
