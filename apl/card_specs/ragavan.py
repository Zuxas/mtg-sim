"""Ragavan, Nimble Pilferer — `{R}` 2/1 menace dash {1}{R}.

Oracle:
  Whenever Ragavan deals combat damage to a player, create a Treasure token,
  then exile top of that player's library. Until end of turn, you may cast
  it. Dash {1}{R}.

Decks using this spec: Boros Energy, Jeskai Blink.

Reference impl: apl/boros_energy.py:RAGAVAN; apl/jeskai_blink_match.py:215-223.

Spec: harness/specs/2026-04-29-card-specs-framework.md
"""
from __future__ import annotations

NAME = "Ragavan, Nimble Pilferer"
DASH_CMC = 2   # {1}{R}


def cast(gs, opponent=None) -> bool:
    """Cast Ragavan from hand if mana available.

    Returns True if cast. Goldfish: just cast and let combat resolve naturally
    (Ragavan attacks via summoning sickness or Arena of Glory haste). Match
    APLs may want to dash via dash() helper instead in some scenarios.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            return True
    return False


def dash(gs, opponent=None) -> bool:
    """Dash Ragavan ({1}{R}, returns to hand at end of turn).

    Goldfish: not useful (Ragavan would just leave the board EOT).
    Match: useful when opp will block but we want a treasure trigger.

    Returns True if dashed. Currently a placeholder; engine support for
    dash mechanic may be incomplete.
    """
    if opponent is None:
        return False  # goldfish-skip
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.total() >= DASH_CMC:
            try:
                gs.mana_pool.pay("{1}{R}", DASH_CMC)
            except Exception:
                continue
            gs.zones.hand.remove(c)
            gs.zones.battlefield.append(c)
            c.turn_entered = gs.turn
            # Dash grants haste, marks for EOT return
            c.summoning_sickness = False
            c.dashed_until_eot = True
            gs._log(f"  Ragavan DASH: enters with haste, returns EOT")
            return True
    return False
