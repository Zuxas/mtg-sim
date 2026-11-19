"""test_no_reactive_sorceries.py -- issue #30.

The reactive window on the opponent's turn accepted Tag.SORCERY, so
Thoughtseize, Duress and sorcery-speed removal were cast at instant speed.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from engine.keywords import KWTag
from engine.match_state import MatchGameState
from engine.match_engine import _try_reactive_interaction
from apl.match_apl import GenericMatchAPL, is_instant_speed


def _card(name, type_line, text, cost="{B}", cmc=1, p=None, t=None, tags=()):
    c = Card(name=name, mana_cost=cost, cmc=cmc, type_line=type_line, oracle_text=text,
             power=p, toughness=t, colors=["B"])
    c.tags = set(getattr(c, "tags", None) or set()) | set(tags)
    return c


def _bear():
    return _card("Grizzly Bears", "Creature - Bear", "", "{1}{G}", 2, "2", "2", {Tag.CREATURE})


def _setup(spell):
    """A's turn. B holds `spell` with 2 mana; A has two Bears in hand and one in play."""
    mgs = MatchGameState([], [], seed=1)
    a, b = mgs.gs_a, mgs.gs_b
    a.zones.hand = [_bear(), _bear()]
    a.zones.battlefield = [_bear()]
    b.zones.hand = [spell]
    b.mana_pool.add("B", 2)
    return mgs, a, b


THOUGHTSEIZE = lambda: _card("Thoughtseize", "Sorcery",
                             "Target player reveals their hand. You choose a nonland card "
                             "from it. That player discards that card. You lose 2 life.",
                             tags={Tag.SORCERY})
SORCERY_KILL = lambda: _card("Sorcery Kill", "Sorcery", "Destroy target creature.",
                             "{1}{B}", 2, tags={Tag.SORCERY})
INSTANT_KILL = lambda: _card("Instant Kill", "Instant", "Destroy target creature.",
                             "{1}{B}", 2, tags={Tag.INSTANT})


def test_sorcery_discard_is_not_cast_on_the_opponents_turn():
    spell = THOUGHTSEIZE()
    mgs, a, b = _setup(spell)
    a.turn = b.turn = 1
    _try_reactive_interaction(GenericMatchAPL(), b, a, mgs, 'b')
    assert spell in b.zones.hand and len(a.zones.hand) == 2


def test_sorcery_removal_is_not_cast_on_the_opponents_turn():
    spell = SORCERY_KILL()
    mgs, a, b = _setup(spell)
    _try_reactive_interaction(GenericMatchAPL(), b, a, mgs, 'b')
    assert spell in b.zones.hand and len(a.zones.battlefield) == 1


def test_instant_removal_still_is():
    spell = INSTANT_KILL()
    mgs, a, b = _setup(spell)
    _try_reactive_interaction(GenericMatchAPL(), b, a, mgs, 'b')
    assert spell not in b.zones.hand, "an instant must still be castable in the reactive window"


def test_apl_override_cannot_sneak_a_sorcery_through():
    class Cheater(GenericMatchAPL):
        def respond_to_spell(self, gs, opponent, spell):
            return gs.zones.hand[0]
    spell = SORCERY_KILL()
    instant = INSTANT_KILL()
    mgs, a, b = _setup(spell)
    b.zones.hand.append(instant)       # so the window opens at all
    _try_reactive_interaction(Cheater(), b, a, mgs, 'b')
    assert spell in b.zones.hand and len(a.zones.battlefield) == 1


def test_flash_counts_as_instant_speed():
    flash = _card("Flash Guy", "Creature - Wizard", "Flash", tags={Tag.CREATURE, KWTag.FLASH})
    assert is_instant_speed(flash) and is_instant_speed(INSTANT_KILL())
    assert not is_instant_speed(SORCERY_KILL()) and not is_instant_speed(_bear())


if __name__ == "__main__":
    test_sorcery_discard_is_not_cast_on_the_opponents_turn()
    test_sorcery_removal_is_not_cast_on_the_opponents_turn()
    test_instant_removal_still_is()
    test_apl_override_cannot_sneak_a_sorcery_through()
    test_flash_counts_as_instant_speed()
    print("test_no_reactive_sorceries: OK")
