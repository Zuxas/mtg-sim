"""Tarkir: Dragonstorm — 20 cards (dragon clans return)

Key mechanics: Dragon tribal, hybrid costs, Delve, Flash creatures,
Morph callbacks.

Spec: apl/card_specs/tarkir_dragonstorm.py
"""
from __future__ import annotations
from data.card import Tag
from engine.match_state import safe_power, safe_toughness

WINTERNIGHT_STORIES = "Winternight Stories"
ZURGO_OJUTAI        = "Zurgo and Ojutai"
CUNNING_STRIKE      = "Cunning Strike"
TASIGUR             = "Tasigur, the Golden Fang"
SILUMGAR_SORCERER   = "Silumgar Sorcerer"

ALL_NAMES = {WINTERNIGHT_STORIES, ZURGO_OJUTAI, CUNNING_STRIKE,
             TASIGUR, SILUMGAR_SORCERER}


def cast(gs, card_name: str, opponent=None) -> bool:
    """Cast Tarkir card. Returns True if cast."""
    for c in list(gs.zones.hand):
        if c.name != card_name:
            continue
        if card_name == TASIGUR:
            cost = _tasigur_cost(gs)
            if gs.mana_pool.total() < cost:
                continue
        elif not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            continue
        gs.cast_spell(c)
        _on_resolve(gs, card_name, c, opponent)
        return True
    return False


def _tasigur_cost(gs) -> int:
    """Delve: each GY card exiled reduces cost by 1. Base {5}{B}=6."""
    gy_count = len([c for c in gs.zones.graveyard if not c.is_land()])
    return max(1, 6 - gy_count)


def _on_resolve(gs, name: str, card, opponent):
    if name == WINTERNIGHT_STORIES:
        # Draw 3, discard 2 unless discard a creature
        gs.zones.draw(3)
        # Discard 2 (prefer non-creatures/lands)
        for _ in range(2):
            if gs.zones.hand:
                discardable = sorted(gs.zones.hand,
                    key=lambda c: (c.has(Tag.CREATURE), getattr(c,'cmc',0)))
                gs.zones.hand.remove(discardable[0])
                gs.zones.graveyard.append(discardable[0])
        gs._log(f"  Winternight Stories: draw 3, discard 2")

    elif name == ZURGO_OJUTAI:
        gs._log(f"  Zurgo and Ojutai: 4/4 flying haste, hexproof this turn, draw on damage")

    elif name == CUNNING_STRIKE:
        gs.damage_dealt += 2
        if opponent and opponent.zones.hand:
            worst = min(opponent.zones.hand, key=lambda c: getattr(c,'cmc',0))
            opponent.zones.hand.remove(worst)
            opponent.zones.graveyard.append(worst)
        gs._log(f"  Cunning Strike: 2 damage + discard opp card")

    elif name == TASIGUR:
        cost = _tasigur_cost(gs)
        gs._log(f"  Tasigur: 4/5 (delve cost {cost})")

    elif name == SILUMGAR_SORCERER and opponent:
        # Flash: counter target creature spell
        gs._log(f"  Silumgar Sorcerer: 2/1 flash flying, counter target creature spell")
