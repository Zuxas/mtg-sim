"""Phelia, Exuberant Shepherd — `{1}{W}` flash 1/1.

Oracle:
  Flash. Whenever Phelia attacks, exile up to one other target nonland
  permanent. At beginning of next end step, return it to the battlefield
  under its owner's control. Put a +1/+1 counter on Phelia if a permanent
  under your control was exiled this way.

Decks using this spec: Jeskai Blink, UW Blink, Esper Blink.

Reference impl: apl/jeskai_blink_match.py:466-484 (attack-trigger logic);
                apl/uw_blink.py + apl/uw_blink_match.py.

Spec: harness/specs/2026-04-29-card-specs-framework.md
"""
from __future__ import annotations

NAME = "Phelia, Exuberant Shepherd"


def cast(gs, opponent=None) -> bool:
    """Cast Phelia (flash 2 mana). Returns True if cast.

    Goldfish: cast on T2 and start attacking. Match: also viable as instant-
    speed defender on opp's end step.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            return True
    return False


def attack_blink_target(gs, etb_creatures: list) -> object | None:
    """Pick best ETB creature on battlefield to blink with Phelia's attack.

    Priority (goldfish-aware): Phlage (3 dmg + 3 life) > Quantum Riddler
    (draw 1) > Casey Jones (draw 3) > Solitude (skip in goldfish — needs
    opponent target).

    Returns the chosen creature or None if no valid target.
    """
    # Goldfish priority order
    goldfish_priority = (
        "Phlage, Titan of Fire's Fury",
        "Quantum Riddler",
        "Casey Jones, Vigilante",
    )
    for name in goldfish_priority:
        for c in etb_creatures:
            if c.name == name:
                return c
    return None


def on_attack(gs, opponent=None) -> None:
    """Phelia's attack trigger handler.

    Goldfish: blink best own ETB creature for re-trigger value.
    Match: optionally exile opponent's best threat instead. Match APLs
    should call this directly with their own targeting logic.

    This is a no-op in pure goldfish if no ETB creatures are on board.
    Caller is responsible for actually triggering the chosen ETB effect
    (since each card's ETB resolution lives in its own card_spec).
    """
    # Goldfish-only path; match APLs handle targeting separately
    if opponent is not None:
        return  # match APL handles its own attack triggers
    # No-op default; goldfish APL composition picks ETB target via
    # attack_blink_target() and dispatches to the chosen card_spec
