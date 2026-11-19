"""Boros Energy's match APL must resolve each enter-the-battlefield effect once.

The APL was written before the engine had handlers for these cards and did the
effects by hand after gs.cast_spell(). The engine now resolves them too, so
each one happened twice: Guide of Souls gave 2 life and 2 energy per creature
(and triggered on itself), Ajani made two Cat Warriors, Seasoned Pyromancer
rummaged twice, and a "self-targeted" Galvanic Discharge also hit the face.

Run: python tests/test_boros_energy_single_etb.py
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.deck import load_deck_from_file
from engine.game_state import GameState
from apl.boros_energy_match import BorosEnergyMatchAPL

DECK, _ = load_deck_from_file("decks/boros_energy_modern.txt")


def _card(name):
    return copy.copy(next(c for c in DECK if c.name == name))


def _turn(board, hand, library=()):
    """One Boros Energy main phase against an empty board. Returns (gs, opp)."""
    gs = GameState(mainboard=[], on_play=True)
    opp = GameState(mainboard=[], on_play=False)
    gs._match_opp, opp._match_opp = opp, gs
    gs.turn = 3
    for name in board:
        c = _card(name)
        c.summoning_sickness = False
        gs.zones.battlefield.append(c)
    gs.land_played = True
    gs.mana_pool.add("R", 3)
    gs.mana_pool.add("W", 3)
    gs.zones.hand = [_card(n) for n in hand]
    gs.zones.library = [_card(n) for n in library]
    BorosEnergyMatchAPL().main_phase_match(gs, opp)
    return gs, opp


def _count(gs, name):
    return sum(1 for c in gs.zones.battlefield if c.name == name)


def test_guide_of_souls_triggers_once_per_creature():
    gs, _ = _turn(["Guide of Souls"], ["Ragavan, Nimble Pilferer"])
    assert _count(gs, "Ragavan, Nimble Pilferer") == 1
    assert gs.life == 21 and gs.energy == 1


def test_guide_of_souls_does_not_trigger_on_itself():
    gs, _ = _turn([], ["Guide of Souls"])
    assert _count(gs, "Guide of Souls") == 1
    assert gs.life == 20 and getattr(gs, "energy", 0) == 0


def test_ajani_makes_one_cat_warrior():
    gs, _ = _turn([], ["Ajani, Nacatl Pariah"])
    cats = [c for c in gs.zones.battlefield if "Cat Warrior" in c.name]
    assert len(cats) == 1, [c.name for c in gs.zones.battlefield]


def test_seasoned_pyromancer_rummages_once():
    gs, _ = _turn([], ["Seasoned Pyromancer", "Mountain", "Mountain"],
                  library=["Plains"] * 6)
    assert _count(gs, "Seasoned Pyromancer") == 1
    # discard 2, draw 2, once: four cards were drawn before this was fixed
    assert len(gs.zones.library) == 4


def test_self_targeted_galvanic_gives_energy_and_no_face_damage():
    gs, opp = _turn(["Guide of Souls"], ["Galvanic Discharge"])
    assert gs.energy == 3
    assert opp.life == 20 and gs.damage_dealt == 0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_boros_energy_single_etb: OK")
