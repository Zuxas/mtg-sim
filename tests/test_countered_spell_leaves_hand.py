"""A countered spell goes to the graveyard and is gone from the hand.

On the default (legacy counter window) path the card was appended to the
graveyard but never removed from the hand. The caster lost the mana, kept the
card, and could cast it again; counterspells never actually cost a card.

Run: python tests/test_countered_spell_leaves_hand.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine.counter_resolver as counter_resolver
from data.card import Card, Tag
from engine.game_state import GameState


def _cast_into_a_counter(card):
    gs = GameState(mainboard=[], on_play=True)
    opp = GameState(mainboard=[], on_play=False)
    gs._match_opp, gs._match_opp_apl = opp, object()
    gs.zones.hand = [card]
    gs.mana_pool.add("R", 3)
    real = counter_resolver.try_counter_spell
    counter_resolver.try_counter_spell = lambda *a, **k: True     # opponent always counters
    try:
        assert gs.cast_spell(card)          # it was cast (and paid for)
    finally:
        counter_resolver.try_counter_spell = real
    return gs, opp


def _zones_holding(gs, card):
    """Every zone the exact card object is in. A card is in one zone."""
    z = gs.zones
    return [name for name in ("hand", "battlefield", "graveyard", "exile", "library")
            for c in getattr(z, name) if c is card]


def test_countered_instant():
    bolt = Card(name="Lightning Bolt", mana_cost="{R}", cmc=1.0, type_line="Instant",
                oracle_text="Lightning Bolt deals 3 damage to any target.")
    bolt.tags = {Tag.INSTANT}
    gs, opp = _cast_into_a_counter(bolt)
    assert bolt not in gs.zones.hand, "countered spell is still in hand"
    assert gs.zones.graveyard.count(bolt) == 1
    assert opp.life == 20 and gs.mana_pool.total() == 2
    assert _zones_holding(gs, bolt) == ["graveyard"]
    # Countering a spell does not undo casting it (prowess still triggers).
    assert gs.spells_cast_this_turn == 1 and gs.noncreature_spells_this_turn == 1


def test_countered_creature():
    bear = Card(name="Test Bear", mana_cost="{1}{R}", cmc=2.0, type_line="Creature - Bear",
                power="2", toughness="2")
    bear.tags = {Tag.CREATURE}
    gs, _ = _cast_into_a_counter(bear)
    assert bear not in gs.zones.hand and bear not in gs.zones.battlefield
    assert gs.zones.graveyard.count(bear) == 1
    assert _zones_holding(gs, bear) == ["graveyard"]
    assert gs.noncreature_spells_this_turn == 0


if __name__ == "__main__":
    test_countered_instant()
    test_countered_creature()
    print("test_countered_spell_leaves_hand: OK")
