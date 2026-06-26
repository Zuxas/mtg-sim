"""test_r1_stack_priority.py -- R1 stack-priority counterspell PROOF tests.

Standalone, plain-assert, ASCII-only. Same conventions as test_determinism.py.
Run:  PYTHONIOENCODING=utf-8 python tests/test_r1_stack_priority.py

Per design harness/specs/2026-06-26-R1-stack-priority-design.md section 4.1, the
proof is a DIFFERENTIAL: each test must be RED on the pre-R1 (legacy) path and
GREEN on the post-R1 (priority-stack) path. The gate is toggled by the control
APL's WANTS_PRIORITY_STACK flag -- the faithful pre-R1 proxy, because with the
gate OFF cast_spell runs the byte-identical legacy counter window
(engine/counter_resolver.py is UNCHANGED) instead of run_priority_stack.

HONEST DEVIATION FROM THE DESIGN (documented, abort-condition A "fix the test"):
  The design's literal TEST 1(c) -- "after the counter resolves, control has
  >= 2 lands with not c.tapped" -- is NOT discriminating against the ACTUAL
  legacy code. counter_resolver._tap_lands_for_response (counter_resolver.py
  ~line 113) fills the response pool via mana_pool.add_land() but NEVER sets
  land.tapped = True. So pre-R1 EVERY land stays untapped -> ">= 2 untapped"
  PASSES pre-R1 -> the test would not falsify (trips abort A). We therefore
  AUGMENT TEST 1 with the real discriminator the design's section 2.4 actually
  describes: REAL mana spend. Post-R1, _pay_for_counter -> tap_lands physically
  TAPS lands (real held-mana spend honoring mana_reserve); pre-R1 zero lands are
  tapped (synthetic tap-agnostic fill). The flipping assertion is
  "tapped_lands >= counter.cmc". We still assert ">= 2 untapped" (reserve held)
  as the spec's land-accounting check; the RED->GREEN axis is the tapped count.

The proof-test results are emitted as a JSON block (PROOF_JSON_BEGIN/END) so the
acceptance harness can fold them into modelability_proofs/.
"""
import sys, os, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from engine.game_state import GameState
from engine.stack import (
    Stack, StackItem, InteractionType, Resolution, resolve_interaction,
)
from engine.priority_stack import run_priority_stack, DEPTH_CAP
from apl.aware_match_apl import AwareMatchAPL
from apl.match_apl import MatchAPL


# ---------------------------------------------------------------------------
# Minimal CONCRETE subclasses. The R1 decision logic (priority_action /
# _r1_choose_counter) is INHERITED unchanged from the shipped AwareMatchAPL --
# only the unrelated abstract stubs (keep/bottom/main_phase) are implemented so
# the class is instantiable. This proves the real shipped decision code, not a
# hand-rolled stub (design 1.5 / advisor item 2).
# ---------------------------------------------------------------------------

class ControlAPL(AwareMatchAPL):
    name = "Control (UW-style)"

    # R1 OPT-IN. Post-narrowing the base AwareMatchAPL ships
    # WANTS_PRIORITY_STACK=False; the opt-in now lives on the control subclass
    # (production: apl/uw_control_modern_match.py). This test's control class
    # mirrors that by flipping the gate on here. Tests that need the pre-R1
    # (legacy) proxy shadow this per-instance with `= False` (test1 pre,
    # test2_pre_red_check).
    WANTS_PRIORITY_STACK = True

    def keep(self, hand, mulligans, on_play):
        return True

    def bottom(self, hand, n):
        return hand[:n]

    def main_phase(self, gs):
        pass


class OppAPL(MatchAPL):
    name = "Opp (threat)"

    def keep(self, hand, mulligans, on_play):
        return True

    def bottom(self, hand, n):
        return hand[:n]

    def main_phase(self, gs):
        pass


# ---------------------------------------------------------------------------
# Card / state construction helpers (hand-placed; no full match, no mulligans)
# ---------------------------------------------------------------------------

def island():
    return Card(name="Island", mana_cost="", cmc=0,
                type_line="Basic Land - Island")


def creature_threat(name="Test Threat"):
    # cmc 4 creature. Counterspell (validity always-True) counters it; the value
    # gate passes because counter_cmc(2) <= spell_value(4).
    return Card(name=name, mana_cost="{2}{B}{B}", cmc=4,
                type_line="Creature - Demon", power="4", toughness="5")


def counterspell():
    # Counterspell: COUNTER_VALIDITY validity = lambda s: True, base_cmc 2.
    return Card(name="Counterspell", mana_cost="{U}{U}", cmc=2,
                type_line="Instant", oracle_text="Counter target spell.")


def negate():
    # Negate: COUNTER_VALIDITY validity = noncreature, base_cmc 2 ({1}{U}).
    return Card(name="Negate", mana_cost="{1}{U}", cmc=2,
                type_line="Instant",
                oracle_text="Counter target noncreature spell.")


def burn():
    return Card(name="Lightning Bolt", mana_cost="{R}", cmc=1,
                type_line="Instant",
                oracle_text="Lightning Bolt deals 3 damage to any target.")


def make_gs(battlefield=None, hand=None, pool=None, mana_reserve=0):
    gs = GameState([], on_play=True)
    gs.zones.battlefield = list(battlefield or [])
    gs.zones.hand = list(hand or [])
    gs.zones.graveyard = []
    gs.turn = 3
    gs.mana_reserve = mana_reserve
    if pool:
        for color, amt in pool.items():
            gs.mana_pool.add(color, amt)
    return gs


def wire(a, a_apl, b, b_apl):
    """Wire two GameStates as opponents, both directions (design 1.4)."""
    a._self_apl = a_apl
    a._match_opp = b
    a._match_opp_apl = b_apl
    b._self_apl = b_apl
    b._match_opp = a
    b._match_opp_apl = a_apl


def n_tapped(gs):
    return sum(1 for l in gs.zones.lands_on_battlefield() if l.tapped)


def n_untapped(gs):
    return sum(1 for l in gs.zones.lands_on_battlefield() if not l.tapped)


# ---------------------------------------------------------------------------
# TEST 1 -- counter fires WITH real mana-hold spend (differential)
# ---------------------------------------------------------------------------

def _run_test1_once(gate_on):
    """One TEST-1 scenario. Returns observed dict.

    Opp (active, plain MatchAPL) casts a flagged threat. Control (AwareMatchAPL,
    holding 4 Islands with mana_reserve=2, Counterspell in hand) responds.
    """
    control_apl = ControlAPL()
    control_apl.name = "Control (UW-style)"
    # Toggle the R1 gate. The test's ControlAPL opts in by default (post-narrowing
    # the production opt-in lives on the control subclass); forcing it False here
    # is the faithful pre-R1 proxy (legacy synchronous window runs).
    control_apl.WANTS_PRIORITY_STACK = gate_on

    opp_apl = OppAPL()                 # plain; WANTS_PRIORITY_STACK=False
    opp_apl.name = "Opp (threat)"

    lands = [island() for _ in range(4)]
    control = make_gs(battlefield=lands, hand=[counterspell()], mana_reserve=2)
    threat = creature_threat("Sheoldred-like Threat")
    # Pre-fill opp's pool so cast_spell's affordability check passes.
    opp = make_gs(hand=[threat], pool={"B": 2, "C": 2})

    wire(opp, opp_apl, control, control_apl)

    result = opp.cast_spell(threat)

    countered = (threat in opp.zones.graveyard
                 and threat not in opp.zones.battlefield)
    counter_in_gy = any(c.name == "Counterspell"
                        for c in control.zones.graveyard)
    counter_in_hand = any(c.name == "Counterspell" for c in control.zones.hand)
    counter_cmc = 2
    return {
        "gate_on": gate_on,
        "cast_returned": bool(result),
        "threat_countered": countered,           # (a)
        "counter_in_graveyard": counter_in_gy,    # (b)
        "counter_left_hand": not counter_in_hand,
        "lands_tapped": n_tapped(control),        # discriminator
        "lands_untapped": n_untapped(control),    # (c) reserve check
        "real_spend": n_tapped(control) >= counter_cmc,
        "reserve_held": n_untapped(control) >= 2,
    }


def test1_differential():
    pre = _run_test1_once(gate_on=False)    # legacy path
    post = _run_test1_once(gate_on=True)    # priority-stack path

    print("  TEST1 pre (gate OFF):", json.dumps(pre))
    print("  TEST1 post (gate ON):", json.dumps(post))

    # The threat is countered on BOTH paths (legacy try_counter_spell also
    # counters); the differential is the REAL mana spend.
    assert post["threat_countered"], "post: threat not countered"
    assert post["counter_in_graveyard"], "post: counter not in graveyard"
    assert post["counter_left_hand"], "post: counter not removed from hand"
    assert post["real_spend"], (
        f"post: counter did not really tap lands "
        f"(tapped={post['lands_tapped']})")
    assert post["reserve_held"], (
        f"post: reserve not honored (untapped={post['lands_untapped']})")

    # RED pre-R1: the discriminator (real spend) MUST fail on the legacy path.
    assert not pre["real_spend"], (
        "ABORT A: TEST1 not falsifying -- legacy path also tapped real lands "
        f"(tapped={pre['lands_tapped']}); the differential is not discriminating")

    print("  TEST1 PASS (RED pre / GREEN post on real-spend discriminator)")
    return {"pre": pre, "post": post}


# ---------------------------------------------------------------------------
# TEST 2 -- depth-2 counter war (counter-the-counter)
# ---------------------------------------------------------------------------

def test2a_stack_depth_and_counter_by_id():
    """Stack-level unit: depth>=2 reachable AND counter(uid) is positional-safe.

    The genuine bug the design fixes: counter_top() marks items[-2] POSITIONALLY,
    which is wrong at depth>=2. counter(uid) must mark the item BY ID regardless
    of position.
    """
    st = Stack()
    a = st.cast(creature_threat("Original"), "caster")
    b = st.cast(counterspell(), "opp")        # counters a
    c = st.cast(negate(), "caster")           # counters b
    assert st.max_depth >= 2, f"stack never reached depth 2 (max={st.max_depth})"
    assert st.max_depth == 3, f"expected depth 3, got {st.max_depth}"

    # Counter the BOTTOM item by uid while two items sit above it. Positional
    # counter_top() would have marked items[-2] (b); counter(uid) must mark a.
    ok = st.counter(a.uid)
    assert ok, "counter(uid) failed to find the target item"
    assert a.countered, "counter(uid) did not mark the targeted item"
    assert not b.countered and not c.countered, (
        "counter(uid) marked the wrong item (positional bug not fixed)")
    print(f"  TEST2a PASS (max_depth={st.max_depth}, counter-by-id correct)")
    return {"max_depth": st.max_depth, "counter_by_id_correct": True}


def test2b_counter_war_resolves_original():
    """End-to-end: control casts a must-resolve spell; opp counters; control
    counters the counter; the ORIGINAL resolves (lands on battlefield)."""
    control_apl = ControlAPL()
    control_apl.name = "Control A"
    opp_apl = ControlAPL()                 # opp ALSO interaction-capable
    opp_apl.name = "Control B"

    spell = creature_threat("Must-Resolve Threat")
    # control casts `spell`, then needs mana to Negate opp's Counterspell.
    control = make_gs(hand=[spell, negate()], pool={"B": 2, "U": 1, "C": 4})
    opp = make_gs(hand=[counterspell()], pool={"U": 2})
    wire(control, control_apl, opp, opp_apl)

    result = control.cast_spell(spell)

    original_resolved = (spell in control.zones.battlefield
                         and spell not in control.zones.graveyard)
    opp_counter_spent = any(c.name == "Counterspell"
                            for c in opp.zones.graveyard)
    control_counter_spent = any(c.name == "Negate"
                                for c in control.zones.graveyard)
    obs = {
        "cast_returned": bool(result),
        "original_resolved": original_resolved,
        "opp_counter_in_graveyard": opp_counter_spent,
        "control_counter_in_graveyard": control_counter_spent,
    }
    print("  TEST2b:", json.dumps(obs))
    assert original_resolved, "original spell did not resolve after counter war"
    # Both counters being spent proves the war reached depth 3 (orig+2 counters).
    assert opp_counter_spent, "opp's counter was never cast (no war happened)"
    assert control_counter_spent, "control never countered the counter"
    print("  TEST2b PASS (counter-the-counter -> original resolves)")
    return obs


def test2_pre_red_check():
    """Pre-R1 (gate OFF) cannot win a counter war: the legacy one-shot window
    forbids counter-the-counter (_in_counter_window guard), so the opponent's
    counter sticks and the original is COUNTERED (does not resolve)."""
    control_apl = ControlAPL()
    control_apl.WANTS_PRIORITY_STACK = False  # gate OFF -> legacy path
    opp_apl = ControlAPL()
    opp_apl.WANTS_PRIORITY_STACK = False

    spell = creature_threat("Must-Resolve Threat")
    control = make_gs(hand=[spell, negate()], pool={"B": 2, "U": 1, "C": 4})
    opp = make_gs(hand=[counterspell()], pool={"U": 2})
    wire(control, control_apl, opp, opp_apl)

    control.cast_spell(spell)
    original_resolved = (spell in control.zones.battlefield
                         and spell not in control.zones.graveyard)
    print(f"  TEST2 pre (gate OFF): original_resolved={original_resolved}")
    assert not original_resolved, (
        "ABORT: legacy path resolved the original through a counter -- "
        "counter war is not actually being proven by the new path")
    return {"original_resolved_pre": original_resolved}


# ---------------------------------------------------------------------------
# TEST 3 -- countered spell takes ZERO effect (check-before-effect)
# ---------------------------------------------------------------------------

def test3a_countered_creature_no_etb():
    """A countered permanent NEVER enters the battlefield (zero ETB). Compared
    against the same permanent resolving when no counter is available."""
    # Countered case.
    ctrl_apl = ControlAPL()
    opp_apl = OppAPL()
    threat = creature_threat("Bringer Threat")
    control = make_gs(battlefield=[island(), island()],
                      hand=[counterspell()], mana_reserve=0)
    opp = make_gs(hand=[threat], pool={"B": 2, "C": 2})
    wire(opp, opp_apl, control, ctrl_apl)
    opp.cast_spell(threat)
    countered_on_bf = threat in opp.zones.battlefield
    countered_in_gy = threat in opp.zones.graveyard

    # Resolving case (control has NO counter -> must resolve).
    ctrl_apl2 = ControlAPL()
    opp_apl2 = OppAPL()
    threat2 = creature_threat("Bringer Threat 2")
    control2 = make_gs(battlefield=[island(), island()], hand=[])
    opp2 = make_gs(hand=[threat2], pool={"B": 2, "C": 2})
    wire(opp2, opp_apl2, control2, ctrl_apl2)
    opp2.cast_spell(threat2)
    resolved_on_bf = threat2 in opp2.zones.battlefield

    obs = {
        "countered_on_battlefield": countered_on_bf,
        "countered_in_graveyard": countered_in_gy,
        "uncountered_on_battlefield": resolved_on_bf,
    }
    print("  TEST3a:", json.dumps(obs))
    assert not countered_on_bf, "countered creature still entered the battlefield"
    assert countered_in_gy, "countered creature not in graveyard"
    assert resolved_on_bf, "control: uncountered creature failed to resolve"
    print("  TEST3a PASS (countered permanent = zero ETB)")
    return obs


def test3b_countered_burn_zero_damage():
    """At the resolution layer, a countered burn applies ZERO damage; an
    identical UN-countered burn applies its damage (positive control)."""
    caster = make_gs()
    target = make_gs()
    target.life = 20

    bolt = burn()
    item = StackItem(card=bolt, caster="a",
                     interaction_type=InteractionType.BURN, damage=3)

    # Countered: resolve_interaction must early-return, life unchanged.
    resolve_interaction(Resolution(item, "countered"), caster, target)
    life_after_countered = target.life

    # Uncountered: same item resolves, deals 3.
    resolve_interaction(Resolution(item, "resolved"), caster, target)
    life_after_resolved = target.life

    obs = {
        "life_after_countered": life_after_countered,
        "life_after_resolved": life_after_resolved,
    }
    print("  TEST3b:", json.dumps(obs))
    assert life_after_countered == 20, "countered burn dealt damage (nonzero effect)"
    assert life_after_resolved == 17, "uncountered burn did not deal 3 (control)"
    print("  TEST3b PASS (countered burn = zero damage)")
    return obs


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main():
    results = {}
    print("TEST 1 -- counter fires with real mana-hold spend (differential)")
    results["test1"] = test1_differential()
    print("TEST 2 -- depth-2 counter war")
    results["test2_pre"] = test2_pre_red_check()
    results["test2a"] = test2a_stack_depth_and_counter_by_id()
    results["test2b"] = test2b_counter_war_resolves_original()
    print("TEST 3 -- countered spell takes zero effect")
    results["test3a"] = test3a_countered_creature_no_etb()
    results["test3b"] = test3b_countered_burn_zero_damage()

    print("PROOF_JSON_BEGIN")
    print(json.dumps(results, indent=2))
    print("PROOF_JSON_END")
    print("ALL R1 PROOF TESTS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
