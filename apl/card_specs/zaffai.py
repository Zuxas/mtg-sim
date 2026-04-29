"""Zaffai and the Tempests — {5}{U}{R} 5/7 Legendary Creature

Oracle:
  Once during each of your turns, you may cast an instant or sorcery spell
  from your hand without paying its mana cost.

Decks: Izzet Cauldron finisher, any Standard Izzet.

Key decisions:
- Cast T7 (5UR). 5/7 body.
- Once per turn: cast the most expensive instant/sorcery in hand for free.
  Priority: Magma Opus (8 mana free), then Mathemagics, then high-CMC removal.
- With Prismari (storm): free spell + storm = massive value.
- With Rootha: free spell before combat = large flying haste token.
- With Veyran: free spell triggers magecraft + doubles other triggers.
- Sequencing: cast Zaffai, then immediately use the free cast (same turn).

Spec: apl/card_specs/zaffai.py
"""
from __future__ import annotations
from data.card import Tag

NAME = "Zaffai and the Tempests"
CMC = 7  # {5}{U}{R}


def cast(gs, opponent=None) -> bool:
    """Cast Zaffai T7. Immediately use the free cast ability.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            gs._log(f"  Zaffai: 5/7, free instant/sorcery from hand once per turn")
            # Immediately try the free cast
            use_free_cast(gs, opponent)
            return True
    return False


def is_active(gs) -> bool:
    """True if Zaffai is on the battlefield."""
    return any(c.name == NAME for c in gs.zones.battlefield)


def use_free_cast(gs, opponent=None) -> bool:
    """Cast the most valuable instant/sorcery from hand without paying its mana cost.

    Prioritizes highest CMC (most value from free cost reduction).
    Returns True if a spell was cast for free.
    """
    if not is_active(gs):
        return False
    if getattr(gs, '_zaffai_used_this_turn', False):
        return False  # once per turn limit

    spells = [c for c in gs.zones.hand
              if not c.is_land() and not c.has(Tag.CREATURE)
              and not c.has(Tag.ENCHANTMENT) and not c.has(Tag.ARTIFACT)]
    if not spells:
        return False

    # Pick the highest-CMC spell for maximum value
    target = max(spells, key=lambda c: getattr(c, 'cmc', 0))
    if getattr(target, 'cmc', 0) < 2:
        return False  # not worth using free cast on cantrips

    gs.zones.hand.remove(target)
    gs.zones.graveyard.append(target)
    gs._zaffai_used_this_turn = True
    gs._log(f"  Zaffai free cast: {target.name} (CMC {getattr(target,'cmc',0)}, cost {0})")
    return True


def reset_turn_flag(gs) -> None:
    """Reset per-turn free cast flag at start of turn."""
    gs._zaffai_used_this_turn = False
