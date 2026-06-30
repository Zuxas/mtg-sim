"""
tests/test_combo_interaction_inert.py

Proves the combo-interaction layer (engine/combo_interaction.py, spec
harness/specs/2026-06-30-modern-combo-interaction.md Component 1) is INERT in
the spine increment:

  1. offer_interaction() with the capability gate OFF
     (WANTS_COMBO_INTERACTION = False) returns disrupted=False and MUTATES
     NOTHING -- no combo zone list (hand/battlefield/graveyard) changes
     (guards the capability gate; spec Component 6.4).
  2. Even an opted-IN APL that PASSES (answer_combo -> None) leaves every zone
     untouched.
  3. The production BorosEnergyMatchAPL inherits answer_combo (the mixin) but
     keeps WANTS_COMBO_INTERACTION = False -> the layer is unreachable for it
     this increment, so adding the mixin is behaviorally inert.

Run: python tests/test_combo_interaction_inert.py   (also pytest-collectable)
"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.combo_interaction import (
    offer_interaction, ComboEvent, InteractionResult, AnswerComboMixin,
    COUNTER_WINDOW, REANIMATE, GY_SETUP, RESOLVE_THREAT, DISCARD,
)


class _Zones:
    def __init__(self, hand, battlefield, graveyard):
        self.hand = hand
        self.battlefield = battlefield
        self.graveyard = graveyard


class _FakeGS:
    def __init__(self, hand=None, bf=None, gy=None):
        self.zones = _Zones(hand or [], bf or [], gy or [])


class _Card:
    def __init__(self, name):
        self.name = name
    def is_land(self):
        return False


class _GateOffAPL:
    WANTS_COMBO_INTERACTION = False
    def answer_combo(self, *a, **k):       # should NEVER be called (gate off)
        raise AssertionError("answer_combo called while gate OFF")


class _GateOnButPasses(AnswerComboMixin):
    WANTS_COMBO_INTERACTION = True
    def answer_combo(self, my_gs, combo_gs, event):
        return None                        # always pass


def _snapshot(gs):
    return ([id(c) for c in gs.zones.hand],
            [id(c) for c in gs.zones.battlefield],
            [id(c) for c in gs.zones.graveyard])


def _events():
    body = _Card("Archon of Cruelty")
    spell = _Card("Goryo's Vengeance")
    return [
        ComboEvent(kind=COUNTER_WINDOW, spell=spell),
        ComboEvent(kind=REANIMATE, targets=[body]),
        ComboEvent(kind=RESOLVE_THREAT, targets=[body]),
        ComboEvent(kind=GY_SETUP, gy_cards=[body]),
        ComboEvent(kind=DISCARD, targets=[spell]),
    ]


def test_gate_off_is_noop_and_mutates_nothing():
    opp_apl = _GateOffAPL()
    for ev in _events():
        combo_gs = _FakeGS(hand=[ev.spell] if ev.spell else [_Card("x")],
                           bf=list(ev.targets), gy=list(ev.gy_cards))
        opp_gs = _FakeGS(hand=[_Card("Lightning Bolt")])
        before_combo = _snapshot(combo_gs)
        before_opp = _snapshot(opp_gs)
        res = offer_interaction(combo_gs, None, opp_gs, opp_apl, ev)
        assert isinstance(res, InteractionResult)
        assert res.disrupted is False, f"gate-off must not disrupt ({ev.kind})"
        assert _snapshot(combo_gs) == before_combo, f"combo zones mutated ({ev.kind})"
        assert _snapshot(opp_gs) == before_opp, f"opp zones mutated ({ev.kind})"


def test_gate_on_but_passing_mutates_nothing():
    opp_apl = _GateOnButPasses()
    for ev in _events():
        combo_gs = _FakeGS(hand=[ev.spell] if ev.spell else [_Card("x")],
                           bf=list(ev.targets), gy=list(ev.gy_cards))
        opp_gs = _FakeGS(hand=[_Card("Lightning Bolt")])
        before_combo = _snapshot(combo_gs)
        res = offer_interaction(combo_gs, None, opp_gs, opp_apl, ev)
        assert res.disrupted is False, f"passing answer must not disrupt ({ev.kind})"
        assert _snapshot(combo_gs) == before_combo, f"combo zones mutated ({ev.kind})"


def test_boros_inherits_mixin_but_gate_stays_off():
    from apl.boros_energy_match import BorosEnergyMatchAPL
    apl = BorosEnergyMatchAPL()
    assert isinstance(apl, AnswerComboMixin), "Boros must inherit AnswerComboMixin"
    assert hasattr(apl, "answer_combo"), "Boros must expose answer_combo"
    assert apl.WANTS_COMBO_INTERACTION is False, \
        "Boros must NOT opt in during the spine increment"


def main():
    test_gate_off_is_noop_and_mutates_nothing()
    test_gate_on_but_passing_mutates_nothing()
    test_boros_inherits_mixin_but_gate_stays_off()
    print("PASS: combo-interaction layer is inert "
          "(gate-off no-op, opted-in-pass no-op, Boros mixin gate OFF).")


if __name__ == "__main__":
    main()
