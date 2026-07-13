"""MatchGameState/bo3 fidelity test: Reckless Pyrosurfer battle cry must fire in the
match_STATE combat path (engine/match_state.py::resolve_combat) -- the gauntlet
`_run_fair` field-read path -- not only in match_runner and goldfish.

Background: match_state.resolve_combat computed attacker damage via safe_power ->
Card.effective_power, which EXCLUDES _battle_cry_instances, so the field-read cell
silently dropped the Low Curve Boros "Voice -> Pyrosurfer" battle-cry line (2026-07-13
bob run bob-20260713-014937-9d75; IMPERFECTION bo3-run_fair-vs-run_match-divergence).
This pins the fix AND -- critically -- the attacker power RESTORE (an unrestored pump
leaks across turns on persistent battlefield cards; byte-identity would NOT catch it).

Run: python tests/test_pyrosurfer_battlecry_matchstate.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from engine.match_state import resolve_combat


def _creature(name, power, tough, type_line="Creature - Human"):
    c = Card(name=name, mana_cost="{1}{R}", cmc=2.0, type_line=type_line)
    c.power = str(power)
    c.toughness = str(tough)
    c.tags = {Tag.CREATURE}
    c.counters = 0
    c.tapped = False
    c.summoning_sickness = False
    return c


def _board(pyro_landfalls):
    voice = _creature("Voice of Victory", 1, 3)
    w1 = _creature("Warrior Token", 1, 1, "Token Creature - Warrior")
    w2 = _creature("Warrior Token", 1, 1, "Token Creature - Warrior")
    pyro = _creature("Reckless Pyrosurfer", 2, 2)
    pyro._battle_cry_instances = pyro_landfalls
    return voice, w1, w2, pyro


def test_11_damage_line_in_matchstate():
    """2 landfall on Pyro -> each OTHER attacker +2/+0: Voice(1->3)+W(1->3)+W(1->3)+Pyro(2)=11."""
    voice, w1, w2, pyro = _board(pyro_landfalls=2)
    res = resolve_combat([voice, w1, w2, pyro], {}, "a", None)
    assert res.damage_to_defender == 11, (
        f"expected 11 (battle cry consumed in match_state), got {res.damage_to_defender}; "
        f"{'5 means resolve_combat still ignores _battle_cry_instances (fix not applied)' if res.damage_to_defender == 5 else ''}")
    print(f"  [ok] match_state combat: 2 landfall -> {res.damage_to_defender} dmg (battle cry fires)")


def test_power_RESTORED_after_matchstate_combat():
    """THE LEAK CHECK: every attacker's .power == pre-combat value after resolve_combat returns."""
    voice, w1, w2, pyro = _board(pyro_landfalls=2)
    before = {id(c): c.power for c in (voice, w1, w2, pyro)}
    resolve_combat([voice, w1, w2, pyro], {}, "a", None)
    for c in (voice, w1, w2, pyro):
        assert c.power == before[id(c)], (
            f"POWER LEAK: {c.name} .power={c.power} != pre-combat {before[id(c)]} "
            f"(unrestored battle-cry pump compounds across turns)")
    assert int(pyro.power) == 2, f"Pyrosurfer self-pumped/not restored: {pyro.power}"
    print("  [ok] match_state combat: ALL attacker powers restored (no cross-turn leak)")


def test_no_landfall_no_battlecry_matchstate():
    voice, w1, w2, pyro = _board(pyro_landfalls=0)
    res = resolve_combat([voice, w1, w2, pyro], {}, "a", None)
    assert res.damage_to_defender == 5, f"expected 5 (no battle cry), got {res.damage_to_defender}"
    print(f"  [ok] match_state combat: 0 landfall -> {res.damage_to_defender} dmg, no battle cry")


def test_toughness_unchanged_matchstate():
    voice, w1, w2, pyro = _board(pyro_landfalls=2)
    resolve_combat([voice, w1, w2, pyro], {}, "a", None)
    assert int(voice.toughness) == 3 and int(w1.toughness) == 1, "battle cry wrongly touched toughness"
    print("  [ok] match_state combat: toughness unchanged (+1/+0)")


if __name__ == "__main__":
    test_11_damage_line_in_matchstate()
    test_power_RESTORED_after_matchstate_combat()
    test_no_landfall_no_battlecry_matchstate()
    test_toughness_unchanged_matchstate()
    print("ALL PASS: battle cry fires in match_state.resolve_combat + attacker power restored")
