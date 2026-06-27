"""R5 PROOF harness -- planeswalker loyalty over turns (match_runner path).

Differential proof (RED gate-OFF / GREEN gate-ON via a per-instance
WANTS_PW_LOYALTY toggle, the R1/R2-proven technique). Built against
match_runner's FLAT TwoPlayerGameState (bf_a/bf_b, life_a/life_b, gy_a/gy_b)
and driven through the GATED runner call sites (_run_pw_activations,
_resolve_combat) -- NOT the gate-agnostic orchestrator -- so a RED assertion
can ONLY fail for a loyalty/attackability reason, never a gate-bypass.

The discriminator axis is pinned (design 0.3): loyalty-over-turns,
ultimate-fires, attackable-dies. One-shot ETB is irrelevant here -- cards are
hand-placed on the battlefield, so no ETB confound.

Run: PYTHONIOENCODING=utf-8 python tests/test_r5_planeswalker_loyalty.py
ASCII-only. Exit 0 on pass, 1 on failure.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from engine.keywords import tag_keywords
from engine.game_state import GameState
from engine.match_runner import (TwoPlayerGameState, _run_pw_activations,
                                  _resolve_combat)
from apl.match_apl import MatchAPL
from engine import planeswalkers as pw


# Paired pre(RED, gate-OFF) / post(GREEN, gate-ON) results captured for the
# proof artifact and printed as evidence.
RESULTS = {}


class TronStyleTestAPL(MatchAPL):
    """In-test PW APL: opts into R5 (mirrors production EldraziTronMatchAPL).
    `gate` flips WANTS_PW_LOYALTY to capture the RED pre-state on the SAME
    structures. `forced_change`, when set, overrides the chooser (used to drive
    a self-minus in TEST3)."""
    name = "TronStyleTest"

    def __init__(self, gate=True, forced_change=None):
        self.WANTS_PW_LOYALTY = gate
        self._forced_change = forced_change

    # Abstract-method stubs (BaseAPL requires these; unused by the proof path).
    def keep(self, hand, mulligans, on_play):
        return True

    def bottom(self, hand, n):
        return []

    def main_phase(self, gs):
        return None

    def choose_pw_ability(self, pw_card, gs, opp_gs):
        if self._forced_change is not None:
            return self._forced_change
        from engine.planeswalkers import _default_choose_pw_ability
        return _default_choose_pw_ability(pw_card)


def _pw_card(name, loyalty):
    c = Card(name=name, mana_cost="{7}", cmc=7,
             type_line="Legendary Planeswalker - " + name.split(",")[0].split()[-1],
             power=None, toughness=None, colors=[])
    tag_keywords(c)
    c.loyalty = loyalty
    return c


def _creature(name, power, toughness):
    c = Card(name=name, mana_cost="{2}", cmc=3, type_line="Creature - Test",
             power=str(power), toughness=str(toughness), colors=["G"])
    tag_keywords(c)
    c.summoning_sickness = False
    return c


def _ok(cond, msg):
    print(("  ok: " if cond else "  FAIL: ") + msg)
    if not cond:
        sys.exit(1)


def _flip(red_pass, green_pass, label):
    """A discriminator must FAIL gate-OFF (RED) and PASS gate-ON (GREEN)."""
    _ok(not red_pass, label + " -- FAILS gate-OFF (RED, discriminating)")
    _ok(green_pass, label + " -- PASSES gate-ON (GREEN)")


# ----------------------------------------------------------------------------
# TEST 1 -- loyalty ticks UP over turns, reaches + fires an ULTIMATE; budget.
# ----------------------------------------------------------------------------
def test1_loyalty_and_ultimate():
    print("TEST 1: loyalty ticks up over turns -> ultimate fires (Karn Liberated)")

    def run(gate):
        pw.reset_fire_count()
        gs = TwoPlayerGameState([], [], on_play=True, seed=42)
        apl = TronStyleTestAPL(gate=gate)
        gs.apl_a, gs.apl_b = apl, TronStyleTestAPL(gate=False)
        karn = _pw_card("Karn Liberated", 6)
        gs.bf_a.append(karn)
        loy_seq = []
        for t in (1, 2, 3):
            gs.turn = t
            _run_pw_activations(gs, "a", apl)
            loy_seq.append(karn.loyalty)
        return {
            "loyalty_by_turn": loy_seq,
            "ultimates": pw.PW_ULTIMATES,
            "activations": pw.PW_ACTIVATIONS,
            "in_gy": karn in gs.gy_a,
            "on_bf": karn in gs.bf_a,
        }

    green = run(True)
    red = run(False)
    RESULTS["test1"] = {"green": green, "red": red}
    print("  GREEN(gate ON):", green)
    print("  RED  (gate OFF):", red)

    # GREEN: 6 -> 10 -> 14 ... but turn 3 fires ult (-14) so loyalty -> 0 -> dies.
    _ok(green["loyalty_by_turn"][0] == 10, "loyalty 6 -> 10 (+4) on turn 1")
    _ok(green["loyalty_by_turn"][1] == 14, "loyalty 10 -> 14 (+4) on turn 2 (strictly increasing)")
    _ok(green["ultimates"] == 1, "ultimate (-14) fired exactly once")
    _ok(green["loyalty_by_turn"][2] == 0, "ultimate paid loyalty 14 -> 0 on turn 3")
    _ok(green["in_gy"] and not green["on_bf"], "0-loyalty SBA put Karn into graveyard")

    # RED (gate OFF): loyalty NEVER changes, no ultimate.
    _ok(red["loyalty_by_turn"] == [6, 6, 6], "RED: loyalty stays 6 every turn (inert)")
    _ok(red["ultimates"] == 0 and red["activations"] == 0, "RED: no activations / ultimates")

    # Discriminators flip.
    _flip(red_pass=(red["loyalty_by_turn"][1] > red["loyalty_by_turn"][0]),
          green_pass=(green["loyalty_by_turn"][1] > green["loyalty_by_turn"][0]),
          label="loyalty strictly increases across turns")
    _flip(red_pass=(red["ultimates"] > 0), green_pass=(green["ultimates"] > 0),
          label="an ultimate fires")

    # Budget (CR 606.3): a SECOND activation on the same PW same turn is rejected.
    pw.reset_fire_count()
    view = GameState(mainboard=[], on_play=True)
    view.turn = 1
    k2 = _pw_card("Karn Liberated", 6)
    view.zones.battlefield.append(k2)
    first = pw.activate_pw_for_turn(k2, view, opp_gs=None, apl=TronStyleTestAPL())
    second = pw.activate_pw_for_turn(k2, view, opp_gs=None, apl=TronStyleTestAPL())
    _ok(first is True and second is False,
        "CR 606.3: 2nd activation same PW same turn rejected (budget)")
    RESULTS["test1"]["budget"] = {"first": first, "second": second}
    print("  PASS TEST 1\n")


# ----------------------------------------------------------------------------
# TEST 2 -- opponent attacks the planeswalker and kills it; face untouched.
# ----------------------------------------------------------------------------
def test2_attackable_pw():
    print("TEST 2: a 4/4 attacks a loyalty-3 Karn -> Karn dies, defender life unchanged")

    def run(gate, atk_power, loyalty):
        pw.reset_fire_count()
        gs = TwoPlayerGameState([], [], on_play=True, seed=42)
        apl = TronStyleTestAPL(gate=gate)
        gs.apl_a, gs.apl_b = apl, TronStyleTestAPL(gate=False)  # attacker (a) opts in -> gate
        gs.life_b = 20
        karn = _pw_card("Karn Liberated", loyalty)
        gs.bf_b.append(karn)                       # defender's walker
        gs.bf_a.append(_creature("Bear", atk_power, atk_power))
        dmg, alost, dlost, llg, dllg, hit = _resolve_combat(gs, "a")
        return {
            "face_damage": dmg,
            "karn_loyalty": karn.loyalty,
            "karn_on_bf": karn in gs.bf_b,
            "karn_in_gy": karn in gs.gy_b,
            "combat_deaths": pw.PW_COMBAT_DEATHS,
        }

    # Lethal sub-case: 4/4 into loyalty-3 walker.
    green = run(True, 4, 3)
    red = run(False, 4, 3)
    RESULTS["test2_lethal"] = {"green": green, "red": red}
    print("  GREEN(gate ON) 4/4 vs loy3:", green)
    print("  RED  (gate OFF) 4/4 vs loy3:", red)

    _ok(green["karn_loyalty"] <= 0, "GREEN: loyalty 3 - 4 <= 0")
    _ok(green["karn_in_gy"] and not green["karn_on_bf"], "GREEN: 0-loyalty SBA -> graveyard")
    _ok(green["face_damage"] == 0, "GREEN: defender face damage == 0 (hit the walker)")
    _ok(green["combat_deaths"] == 1, "GREEN: PW_COMBAT_DEATHS == 1")

    # HONESTY NOTE: gate-OFF the engine has NO attack-the-walker target, so the
    # planeswalker is (legacy quirk) admitted to the blocker pool and absorbs the
    # attacker as a phantom blocker -- the attacker is "blocked", deals 0 to the
    # face, and the walker's LOYALTY is UNCHANGED and is NOT removed via the
    # 0-loyalty SBA. The R5 discriminators are therefore loyalty-change and
    # combat-death (NOT face damage, which is 0 either way). R5 fixes the quirk:
    # gate-ON the walker is excluded from blocking and is properly attackable.
    _ok(red["karn_loyalty"] == 3, "RED: Karn loyalty UNCHANGED at 3 (not attackable)")
    _ok(red["combat_deaths"] == 0, "RED: no PW combat death (loyalty SBA never fires)")
    _ok(not red["karn_in_gy"], "RED: Karn not sent to graveyard via loyalty")

    _flip(red_pass=(red["karn_loyalty"] != 3), green_pass=(green["karn_loyalty"] != 3),
          label="combat damage reduces the walker's loyalty")
    _flip(red_pass=(red["combat_deaths"] > 0), green_pass=(green["combat_deaths"] > 0),
          label="the walker dies to combat via the 0-loyalty SBA")

    # Partial-damage survive sub-case: 2/2 into loyalty-6 walker -> loyalty 4, alive.
    surv = run(True, 2, 6)
    RESULTS["test2_survive"] = surv
    print("  GREEN(gate ON) 2/2 vs loy6:", surv)
    _ok(surv["karn_loyalty"] == 4, "survive: loyalty 6 - 2 == 4")
    _ok(surv["karn_on_bf"] and not surv["karn_in_gy"], "survive: walker ALIVE on battlefield")
    _ok(surv["face_damage"] == 0, "survive: defender face damage == 0")
    _ok(surv["combat_deaths"] == 0, "survive: no combat death (partial damage)")
    print("  PASS TEST 2\n")


# ----------------------------------------------------------------------------
# TEST 3 -- a self -ability shares the SAME 0-loyalty SBA (kills the PW at 0).
# ----------------------------------------------------------------------------
def test3_self_minus_shares_sba():
    print("TEST 3: self -ability shares the 0-loyalty SBA (Professor Dellian Fel loy2, -3)")

    def run(gate):
        pw.reset_fire_count()
        gs = TwoPlayerGameState([], [], on_play=True, seed=42)
        apl = TronStyleTestAPL(gate=gate, forced_change=-3)
        gs.apl_a, gs.apl_b = apl, TronStyleTestAPL(gate=False)
        fel = _pw_card("Professor Dellian Fel", 2)
        gs.bf_a.append(fel)
        gs.turn = 1
        _run_pw_activations(gs, "a", apl)
        return {
            "loyalty": fel.loyalty,
            "on_bf": fel in gs.bf_a,
            "in_gy": fel in gs.gy_a,
        }

    green = run(True)
    red = run(False)
    RESULTS["test3"] = {"green": green, "red": red}
    print("  GREEN(gate ON):", green)
    print("  RED  (gate OFF):", red)

    _ok(green["loyalty"] == -1, "GREEN: -3 paid below zero (2 -> -1)")
    _ok(green["in_gy"] and not green["on_bf"],
        "GREEN: same shared 0-loyalty SBA as combat -> graveyard")
    _ok(red["loyalty"] == 2 and red["on_bf"], "RED: minus never selected -> stays at loyalty 2 on bf")

    _flip(red_pass=(not red["on_bf"]), green_pass=(not green["on_bf"]),
          label="self-minus to 0 sends the walker to the graveyard")
    print("  PASS TEST 3\n")


if __name__ == "__main__":
    test1_loyalty_and_ultimate()
    test2_attackable_pw()
    test3_self_minus_shares_sba()
    print("ALL R5 PROOF TESTS PASS")
    # Emit captured paired results for the proof artifact.
    import json
    print("RESULTS_JSON " + json.dumps(RESULTS))
    sys.exit(0)
