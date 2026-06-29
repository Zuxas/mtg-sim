"""Stand-alone unit tests for apl/card_specs/ primitives.

Per CONVENTIONS.md: ASCII-only output, sys.path from repo root, exit 0/1,
runnable as `python tests/test_card_specs.py` with PYTHONIOENCODING=utf-8.

Covers the source spec's named cases (phlage / ragavan / phelia / ephemerate)
plus the two new Tier-1 modules (solitude / galvanic_discharge), focusing on
the goldfish-dead guards (opponent=None) that justify each module's contract.

Uses an in-test fake GameState that satisfies exactly the surface the
card_specs functions touch (zones, mana_pool, cast_spell, energy, life,
damage_dealt, turn, _log). Real data.card.Card is used for cards so .has() /
.is_land() behave like production.
"""
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from data.card import Card, Tag
from apl.card_specs import (phlage, ragavan, phelia, ephemerate,
                            solitude, galvanic_discharge)

PHLAGE = "Phlage, Titan of Fire's Fury"
RAGAVAN = "Ragavan, Nimble Pilferer"
PHELIA = "Phelia, Exuberant Shepherd"
EPHEMERATE = "Ephemerate"
QUANTUM = "Quantum Riddler"
CASEY = "Casey Jones, Vigilante"
SOLITUDE = "Solitude"
GALVANIC = "Galvanic Discharge"

_FAILURES = []


def check(cond, msg):
    if cond:
        print("  PASS: " + msg)
    else:
        print("  FAIL: " + msg)
        _FAILURES.append(msg)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

def mk(name, mana_cost="{1}", cmc=1, type_line="Creature - Elemental",
       power="2", toughness="2"):
    return Card(name=name, mana_cost=mana_cost, cmc=cmc, type_line=type_line,
                power=power, toughness=toughness)


class FakeZones:
    def __init__(self):
        self.hand = []
        self.graveyard = []
        self.battlefield = []
        self.exile = []
        self.library = []

    def draw(self, n):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop(0))
            else:
                self.hand.append(mk("Filler Draw"))

    def creatures_on_battlefield(self):
        return [c for c in self.battlefield
                if c.has(Tag.CREATURE) and not c.is_land()]


class FakeManaPool:
    def __init__(self, amount=10):
        self.amount = amount

    def can_cast(self, cost, cmc):
        return self.amount >= cmc

    def can_pay(self, cost, cmc):
        return self.amount >= cmc

    def pay(self, cost, cmc):
        self.amount -= cmc

    def total(self):
        return self.amount


class FakeGS:
    def __init__(self, mana=10):
        self.zones = FakeZones()
        self.mana_pool = FakeManaPool(mana)
        self.damage_dealt = 0
        self.life = 20
        self.turn = 1
        self.energy = 0
        self.logs = []

    def _log(self, m):
        self.logs.append(m)

    def cast_spell(self, card):
        # Emulate the engine: pay mana, move hand->battlefield, fire known ETBs
        # (matches engine/card_handlers_verified.py for the cards under test).
        try:
            self.mana_pool.pay(card.mana_cost, card.cmc)
        except Exception:
            pass
        if card in self.zones.hand:
            self.zones.hand.remove(card)
        self.zones.battlefield.append(card)
        card.turn_entered = self.turn
        if card.name == PHLAGE:
            # Phlage ETB: 3 dmg + 3 life (engine leaves it on battlefield)
            self.damage_dealt += 3
            self.life += 3


class FakeOpp:
    def __init__(self):
        self.zones = FakeZones()
        self.life = 20


# ---------------------------------------------------------------------------
# phlage
# ---------------------------------------------------------------------------

def test_phlage_hardcast():
    print("phlage.hardcast")
    gs = FakeGS(mana=10)
    gs.zones.hand.append(mk(PHLAGE, "{1}{R}{W}", 3, power="6", toughness="6"))
    ok = phlage.hardcast(gs)
    check(ok is True, "hardcast returns True with mana + card in hand")
    check(gs.mana_pool.total() == 7, "hardcast pays 3 mana (10 -> 7)")
    check(gs.damage_dealt == 3, "hardcast ETB adds 3 damage")
    check(gs.life == 23, "hardcast ETB adds 3 life")
    check(any(c.name == PHLAGE for c in gs.zones.battlefield),
          "Phlage ends on battlefield")


def test_phlage_escape_boundary():
    print("phlage.escape boundary (4 vs 5 non-Phlage GY cards)")
    # 4 non-Phlage GY cards -> not enough to exile 5 -> False
    gs = FakeGS(mana=10)
    gs.zones.graveyard.append(mk(PHLAGE, "{1}{R}{W}", 3))
    for i in range(4):
        gs.zones.graveyard.append(mk("Fodder %d" % i))
    check(phlage.escape(gs) is False, "escape False with only 4 non-Phlage GY cards")

    # 5 non-Phlage GY cards -> escape fires
    gs2 = FakeGS(mana=10)
    gs2.zones.graveyard.append(mk(PHLAGE, "{1}{R}{W}", 3))
    for i in range(5):
        gs2.zones.graveyard.append(mk("Fodder %d" % i))
    ok = phlage.escape(gs2)
    check(ok is True, "escape True with 5 non-Phlage GY cards + 4 mana")
    check(gs2.damage_dealt == 3, "escape ETB adds 3 damage")
    check(gs2.life == 23, "escape ETB adds 3 life")
    check(any(c.name == PHLAGE for c in gs2.zones.battlefield),
          "escaped Phlage on battlefield")
    check(len(gs2.zones.exile) == 5, "escape exiles 5 GY cards")


def test_phlage_escape_mana_gate():
    print("phlage.escape mana gate")
    gs = FakeGS(mana=3)  # below ESCAPE_CMC (4)
    gs.zones.graveyard.append(mk(PHLAGE, "{1}{R}{W}", 3))
    for i in range(5):
        gs.zones.graveyard.append(mk("Fodder %d" % i))
    check(phlage.escape(gs) is False, "escape False when mana < 4")


# ---------------------------------------------------------------------------
# ragavan
# ---------------------------------------------------------------------------

def test_ragavan():
    print("ragavan.cast / dash")
    gs = FakeGS(mana=10)
    gs.zones.hand.append(mk(RAGAVAN, "{R}", 1, power="2", toughness="1"))
    check(ragavan.cast(gs) is True, "cast from hand returns True")
    # dash goldfish guard
    gs2 = FakeGS(mana=10)
    gs2.zones.hand.append(mk(RAGAVAN, "{R}", 1, power="2", toughness="1"))
    check(ragavan.dash(gs2, opponent=None) is False,
          "dash returns False when opponent is None (goldfish guard)")


# ---------------------------------------------------------------------------
# phelia
# ---------------------------------------------------------------------------

def test_phelia():
    print("phelia.attack_blink_target priority")
    quantum = mk(QUANTUM, "{1}{U}", 2)
    casey = mk(CASEY, "{2}{W}", 3)
    phl = mk(PHLAGE, "{1}{R}{W}", 3, power="6", toughness="6")
    # Phlage > Quantum > Casey
    check(phelia.attack_blink_target(None, [casey, quantum, phl]) is phl,
          "Phlage chosen over Quantum and Casey")
    check(phelia.attack_blink_target(None, [casey, quantum]) is quantum,
          "Quantum chosen over Casey")
    check(phelia.attack_blink_target(None, [casey]) is casey,
          "Casey chosen when only option")
    check(phelia.attack_blink_target(None, []) is None,
          "returns None on empty board")


# ---------------------------------------------------------------------------
# ephemerate
# ---------------------------------------------------------------------------

def test_ephemerate_noop():
    print("ephemerate.cast no-op when no ETB creature on board")
    gs = FakeGS(mana=10)
    gs.zones.hand.append(mk(EPHEMERATE, "{W}", 1, type_line="Instant",
                            power=None, toughness=None))
    check(ephemerate.cast(gs) is False,
          "cast returns False with no viable ETB creature on battlefield")


def test_ephemerate_retrigger_phlage():
    print("ephemerate._retrigger_etb for Phlage")
    gs = FakeGS(mana=10)
    phl = mk(PHLAGE, "{1}{R}{W}", 3, power="6", toughness="6")
    gs.zones.battlefield.append(phl)
    ephemerate._retrigger_etb(gs, phl)
    check(gs.damage_dealt == 3, "retrigger adds 3 damage")
    check(gs.life == 23, "retrigger adds 3 life")
    check(phl not in gs.zones.battlefield, "Phlage left battlefield (sac re-fired)")
    check(phl in gs.zones.graveyard, "Phlage moved to graveyard")


# ---------------------------------------------------------------------------
# solitude (new)
# ---------------------------------------------------------------------------

def test_solitude_goldfish_guard():
    print("solitude goldfish guards (opponent=None)")
    gs = FakeGS(mana=10)
    gs.zones.hand.append(mk(SOLITUDE, "{3}{W}", 4, power="3", toughness="2"))
    gs.zones.hand.append(mk("Plains Pitch", "{W}", 1, type_line="Land",
                            power=None, toughness=None))
    check(solitude.evoke(gs, opponent=None) is False,
          "evoke returns False when opponent is None")
    check(solitude.cast(gs, opponent=None) is False,
          "cast returns False when opponent is None")


def test_solitude_evoke_positive():
    print("solitude.evoke with opponent")
    gs = FakeGS(mana=10)
    sol = mk(SOLITUDE, "{3}{W}", 4, power="3", toughness="2")
    pitch = mk("White Pitch", "{1}{W}", 2)
    gs.zones.hand.append(sol)
    gs.zones.hand.append(pitch)
    opp = FakeOpp()
    threat = mk("Big Threat", "{4}", 4, power="5", toughness="5")
    opp.zones.battlefield.append(threat)
    ok = solitude.evoke(gs, opponent=opp)
    check(ok is True, "evoke returns True with white pitch + opp threat")
    check(threat in opp.zones.exile, "opp threat exiled")
    check(opp.life == 25, "opp gains life = exiled power (20 + 5)")
    check(pitch in gs.zones.exile, "white card pitched to exile")
    check(sol in gs.zones.battlefield, "Solitude placed on battlefield")


def test_solitude_no_white_card():
    print("solitude.evoke with no white card to pitch")
    gs = FakeGS(mana=10)
    gs.zones.hand.append(mk(SOLITUDE, "{3}{W}", 4, power="3", toughness="2"))
    gs.zones.hand.append(mk("Red Card", "{R}", 1))
    opp = FakeOpp()
    opp.zones.battlefield.append(mk("Big Threat", "{4}", 4, power="5", toughness="5"))
    check(solitude.evoke(gs, opponent=opp) is False,
          "evoke False when no white card in hand to pitch")


# ---------------------------------------------------------------------------
# galvanic_discharge (new)
# ---------------------------------------------------------------------------

def test_galvanic_goldfish_guard():
    print("galvanic.cast_for_damage goldfish guard (opponent=None)")
    gs = FakeGS(mana=10)
    gs.zones.hand.append(mk(GALVANIC, "{R}", 1, type_line="Instant",
                            power=None, toughness=None))
    check(galvanic_discharge.cast_for_damage(gs, opponent=None) is False,
          "cast_for_damage returns False when opponent is None")


def test_galvanic_energy_positive():
    print("galvanic.cast_for_energy (+3 net energy)")
    gs = FakeGS(mana=10)
    gs.zones.battlefield.append(mk("Some Creature", "{1}", 1, power="1", toughness="1"))
    gs.zones.hand.append(mk(GALVANIC, "{R}", 1, type_line="Instant",
                            power=None, toughness=None))
    ok = galvanic_discharge.cast_for_energy(gs)
    check(ok is True, "cast_for_energy returns True with creature on board")
    check(gs.energy == 3, "energy increased by 3")


def test_galvanic_energy_no_creature():
    print("galvanic.cast_for_energy with no creature on board")
    gs = FakeGS(mana=10)
    gs.zones.hand.append(mk(GALVANIC, "{R}", 1, type_line="Instant",
                            power=None, toughness=None))
    check(galvanic_discharge.cast_for_energy(gs) is False,
          "cast_for_energy False with no creature to target")


def test_galvanic_damage_positive():
    print("galvanic.cast_for_damage with opponent")
    gs = FakeGS(mana=10)
    gs.zones.hand.append(mk(GALVANIC, "{R}", 1, type_line="Instant",
                            power=None, toughness=None))
    opp = FakeOpp()
    ok = galvanic_discharge.cast_for_damage(gs, opponent=opp, amount=3)
    check(ok is True, "cast_for_damage returns True with opponent")
    check(opp.life == 17, "opp takes 3 damage (20 -> 17)")
    check(gs.energy == 0, "net energy 0 after spending 3 of 3")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    tests = [
        test_phlage_hardcast,
        test_phlage_escape_boundary,
        test_phlage_escape_mana_gate,
        test_ragavan,
        test_phelia,
        test_ephemerate_noop,
        test_ephemerate_retrigger_phlage,
        test_solitude_goldfish_guard,
        test_solitude_evoke_positive,
        test_solitude_no_white_card,
        test_galvanic_goldfish_guard,
        test_galvanic_energy_positive,
        test_galvanic_energy_no_creature,
        test_galvanic_damage_positive,
    ]
    print("=== card_specs unit tests ===")
    for t in tests:
        t()
    print("")
    if _FAILURES:
        print("RESULT: FAIL (%d failing checks)" % len(_FAILURES))
        for m in _FAILURES:
            print("  - " + m)
        return 1
    print("RESULT: PASS (all checks green)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
