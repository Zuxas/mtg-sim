"""Lorehold, the Historian — {3}{R}{W} 5/5 Legendary Creature — Elder Dragon

Oracle:
  Flying, haste
  Each instant and sorcery card in your hand has miracle {2}. (You may cast
  that card for {2} if it's the first card you drew this turn.)

Decks: Jeskai Control variants, Boros spells.

Key decisions:
- Cast T5 (3RW). 5/5 flying haste attacks immediately.
- Miracle {2}: any instant/sorcery drawn this turn costs only {2}.
  Best case: draw a high-CMC spell first each turn and cast for {2}.
  e.g. Draw Magma Opus (MV 8) → cast for {2} instead of {6}{U}{R}.
  e.g. Draw Supreme Verdict (MV 4) → cast for {2} instead of {2}{W}{W}.
- Miracle applies to the FIRST DRAW each turn (including draw step draw).
- Without tracking draw order precisely: estimate by assuming the turn's
  draw is eligible for miracle, and apply miracle cost to most expensive
  spell in hand if it's an instant/sorcery.
- Combat: 5/5 flying haste deals 5 immediately after cast.

Spec: apl/card_specs/lorehold.py
"""
from __future__ import annotations
from data.card import Tag

NAME = "Lorehold, the Historian"
CMC = 5  # {3}{R}{W}
MIRACLE_COST = 2


def cast(gs, opponent=None) -> bool:
    """Cast Lorehold T5. Haste means immediate 5 damage pressure.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            gs._log(f"  Lorehold: 5/5 flying haste, all drawn spells have miracle {{2}}")
            return True
    return False


def is_active(gs) -> bool:
    """True if Lorehold is on the battlefield."""
    return any(c.name == NAME for c in gs.zones.battlefield)


def miracle_cast(gs, opponent=None) -> bool:
    """Cast the most expensive instant/sorcery in hand for miracle {2}.

    Simulates drawing a spell first this turn (miracle window).
    Returns True if a spell was miracle-cast.
    """
    if not is_active(gs):
        return False

    # Find highest-CMC instant/sorcery in hand
    spell_candidates = [c for c in gs.zones.hand
                        if not c.is_land() and not c.has(Tag.CREATURE)
                        and not c.has(Tag.ENCHANTMENT) and not c.has(Tag.ARTIFACT)
                        and getattr(c, 'cmc', 0) >= 3]  # only worth it for CMC >= 3

    if not spell_candidates:
        return False

    target = max(spell_candidates, key=lambda c: getattr(c, 'cmc', 0))
    if gs.mana_pool.total() < MIRACLE_COST:
        return False

    try:
        gs.mana_pool.pay("{2}", MIRACLE_COST)
    except Exception:
        return False

    gs.zones.hand.remove(target)
    gs.zones.graveyard.append(target)
    gs._log(f"  Lorehold miracle: {target.name} (CMC {getattr(target,'cmc',0)}) "
            f"cast for {{2}}")
    return True


def effective_cost(gs, card) -> int:
    """Return the effective casting cost of a spell with Lorehold active."""
    if not is_active(gs):
        return getattr(card, 'cmc', 0)
    # Miracle applies to the first drawn spell each turn
    return MIRACLE_COST
