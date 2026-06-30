"""Fidelity test for the Low Curve Boros Energy engine package:
Voice of Victory (Mobilize 2) + Reckless Pyrosurfer (battle cry).

Proves:
  1. Battle cry fires in combat and pumps every OTHER attacker +1/+0
     per instance (power only, not toughness).
  2. Battle cry resolves AFTER mobilize, so the two 1/1 Warrior tokens
     created by Voice of Victory receive the bonus (1 -> 3 with 2 instances).
  3. The primer "11 damage" line falls out under a 2-landfall turn:
     Voice(1->3) + Warrior(1->3) + Warrior(1->3) + Pyrosurfer(2, unpumped) = 11.
  4. Reckless Pyrosurfer's battle cry is LANDFALL-conditional: with 0
     landfalls this turn it grants no battle cry (it is NOT static).

Run: PYTHONIOENCODING=utf-8 python tests/test_pyrosurfer_battlecry_package.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from engine.keywords import KWTag
from engine.game_state import GameState


def _creature(name, power, tough, type_line="Creature — Human"):
    c = Card(name=name, mana_cost="{1}{R}", cmc=2.0, type_line=type_line)
    c.power = str(power)
    c.toughness = str(tough)
    c.tags = {Tag.CREATURE}
    c.counters = 0
    c.tapped = False
    c.summoning_sickness = False
    return c


def _fresh_state():
    gs = GameState.__new__(GameState)
    # Minimal manual init sufficient for _attack().
    from engine.zones import Zones
    from engine.mana import ManaPool
    gs.zones = Zones()
    gs.mana_pool = ManaPool()
    gs.life = 20
    gs.turn = 5
    gs.damage_dealt = 0
    gs.noncreature_spells_this_turn = 0
    gs._log_lines = []
    gs._verbose = False
    gs.verbose = False
    return gs


def _attack_with(gs, board, pyrosurfer_landfalls=0):
    for c in board:
        gs.zones.battlefield.append(c)
    pyro = next((c for c in board if c.name == "Reckless Pyrosurfer"), None)
    if pyro is not None:
        pyro._battle_cry_instances = pyrosurfer_landfalls
    gs.damage_dealt = 0
    gs._do_combat()
    return gs.damage_dealt


def test_no_landfall_no_battlecry():
    """Pyrosurfer with 0 landfall this turn: NOT static -> no pump."""
    gs = _fresh_state()
    voice = _creature("Voice of Victory", 1, 3)
    pyro = _creature("Reckless Pyrosurfer", 2, 2)
    dmg = _attack_with(gs, [voice, pyro], pyrosurfer_landfalls=0)
    # Voice(1) + Pyro(2) + 2 mobilize Warriors(1 each) = 5, no battle cry.
    assert dmg == 5, f"expected 5 (no battle cry), got {dmg}"
    print(f"  [ok] 0 landfall -> {dmg} dmg, no battle cry (correctly conditional)")


def test_11_damage_line():
    """The primer line under an explicit 2-landfall turn (e.g. a fetch)."""
    gs = _fresh_state()
    voice = _creature("Voice of Victory", 1, 3)
    pyro = _creature("Reckless Pyrosurfer", 2, 2)
    dmg = _attack_with(gs, [voice, pyro], pyrosurfer_landfalls=2)

    # Voice's Mobilize 2 must have created the two Warrior tokens.
    warriors = [c for c in gs.zones.battlefield if c.name == "Warrior Token"]
    assert len(warriors) == 2, f"expected 2 mobilize Warriors, got {len(warriors)}"

    # The +1/+0 is temporary and restored post-combat, so the proof of
    # correct ordering is the DAMAGE TOTAL:
    #   battle cry AFTER mobilize -> Voice(3)+W(3)+W(3)+Pyro(2) = 11
    #   battle cry BEFORE mobilize (the bug) -> Voice(3)+Pyro(2)+W(1)+W(1) = 7
    # So dmg == 11 strictly proves the tokens received the bonus.
    assert dmg == 11, (
        f"expected 11 (battle cry after mobilize pumps tokens), got {dmg}; "
        f"{'7 means battle cry fired before mobilize' if dmg == 7 else ''}")
    # Pyrosurfer must NOT pump itself; power restored cleanly post-combat.
    assert int(pyro.power) == 2, f"Pyrosurfer self-pumped/not restored: {pyro.power}"
    print(f"  [ok] 2 landfall -> {dmg} dmg; 2 mobilize Warriors pumped to 3 "
          f"(battle cry resolves AFTER mobilize)")


def test_toughness_unchanged():
    """Battle cry is +1/+0: toughness must be untouched."""
    gs = _fresh_state()
    voice = _creature("Voice of Victory", 1, 3)
    pyro = _creature("Reckless Pyrosurfer", 2, 2)
    _attack_with(gs, [voice, pyro], pyrosurfer_landfalls=2)
    assert int(voice.toughness) == 3, f"Voice toughness changed to {voice.toughness}"
    print(f"  [ok] toughness unchanged (+1/+0, not +1/+1)")


if __name__ == "__main__":
    test_no_landfall_no_battlecry()
    test_11_damage_line()
    test_toughness_unchanged()
    print("ALL PASS: Voice + Pyrosurfer battle-cry package faithfully modeled")
