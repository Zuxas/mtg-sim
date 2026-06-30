"""Match-engine fidelity test: Reckless Pyrosurfer battle cry must fire in the
TWO-PLAYER match path (engine/match_runner.py::_resolve_combat), not only in the
goldfish GameState._do_combat path.

Background: on_landfall (engine/card_effects.py) accumulates Pyrosurfer's battle
cry into c._battle_cry_instances during the main phase (via the per-turn GameState
view, whose battlefield aliases TwoPlayerGameState.bf_*). Before this fix the match
combat resolver _resolve_combat never CONSUMED those instances, so the Low Curve
Boros Energy deck's signature Voice-of-Victory -> Reckless-Pyrosurfer "11-damage
line" was modeled in goldfish but DEAD in every gauntlet/match. This test pins the
behavior at the match-combat interface.

Run: PYTHONIOENCODING=utf-8 python tests/test_pyrosurfer_battlecry_match.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from engine.match_runner import TwoPlayerGameState, _resolve_combat


def _creature(name, power, tough, type_line="Creature - Human"):
    c = Card(name=name, mana_cost="{1}{R}", cmc=2.0, type_line=type_line)
    c.power = str(power)
    c.toughness = str(tough)
    c.tags = {Tag.CREATURE}
    c.counters = 0
    c.tapped = False
    c.summoning_sickness = False
    return c


def _state(attackers_a):
    """Minimal TwoPlayerGameState: side 'a' attacks into an empty board."""
    gs = TwoPlayerGameState.__new__(TwoPlayerGameState)
    gs.bf_a = list(attackers_a)
    gs.bf_b = []
    gs.noncreature_spells_a = 0
    gs.noncreature_spells_b = 0
    return gs


def _board(pyro_landfalls):
    voice = _creature("Voice of Victory", 1, 3)
    w1 = _creature("Warrior Token", 1, 1, "Token Creature - Warrior")
    w2 = _creature("Warrior Token", 1, 1, "Token Creature - Warrior")
    pyro = _creature("Reckless Pyrosurfer", 2, 2)
    pyro._battle_cry_instances = pyro_landfalls
    return voice, w1, w2, pyro


def test_11_damage_line_in_match_combat():
    """2 landfall instances on Pyrosurfer -> each OTHER attacker +2/+0:
    Voice(1->3) + Warrior(1->3) + Warrior(1->3) + Pyro(2, unpumped) = 11."""
    voice, w1, w2, pyro = _board(pyro_landfalls=2)
    gs = _state([voice, w1, w2, pyro])
    total_dmg = _resolve_combat(gs, "a")[0]
    assert total_dmg == 11, (
        f"expected 11 (battle cry consumed in match combat), got {total_dmg}; "
        f"{'5 means _resolve_combat still ignores _battle_cry_instances' if total_dmg == 5 else ''}")
    # Pyrosurfer must not pump itself; power restored cleanly post-combat.
    assert int(pyro.power) == 2, f"Pyrosurfer self-pumped/not restored: {pyro.power}"
    print(f"  [ok] match combat: 2 landfall -> {total_dmg} dmg (battle cry fires in _resolve_combat)")


def test_no_landfall_no_battlecry_in_match():
    """0 landfall this turn: Pyrosurfer is NOT static -> no pump.
    Voice(1) + Warrior(1) + Warrior(1) + Pyro(2) = 5."""
    voice, w1, w2, pyro = _board(pyro_landfalls=0)
    gs = _state([voice, w1, w2, pyro])
    total_dmg = _resolve_combat(gs, "a")[0]
    assert total_dmg == 5, f"expected 5 (no battle cry), got {total_dmg}"
    print(f"  [ok] match combat: 0 landfall -> {total_dmg} dmg, no battle cry (correctly conditional)")


def test_toughness_unchanged_in_match():
    """Battle cry is +1/+0: toughness must be untouched."""
    voice, w1, w2, pyro = _board(pyro_landfalls=2)
    gs = _state([voice, w1, w2, pyro])
    _resolve_combat(gs, "a")
    assert int(voice.toughness) == 3, f"Voice toughness changed to {voice.toughness}"
    assert int(w1.toughness) == 1, f"Warrior toughness changed to {w1.toughness}"
    print(f"  [ok] match combat: toughness unchanged (+1/+0, not +1/+1)")


if __name__ == "__main__":
    test_11_damage_line_in_match_combat()
    test_no_landfall_no_battlecry_in_match()
    test_toughness_unchanged_in_match()
    print("ALL PASS: Voice + Pyrosurfer battle-cry package fires in the match engine")
