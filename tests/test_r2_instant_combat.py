"""test_r2_instant_combat.py -- R2 instant-speed combat-window PROOF tests.

Standalone, plain-assert, ASCII-only. Same conventions as test_r1_stack_priority.py.
Run:  PYTHONIOENCODING=utf-8 python tests/test_r2_instant_combat.py

Per design harness/specs/2026-06-26-R2-instant-combat-design.md section 4.1 the
proof is a DIFFERENTIAL: each test must be RED on the gate-OFF (legacy
synchronous combat) path and GREEN on the gate-ON (stepped priority-window)
path. The gate is the SAME production gate the engine uses
(engine.match_engine._instant_combat_enabled); it is toggled by the tempo APL's
WANTS_INSTANT_COMBAT flag -- the faithful pre-R2 proxy, because with the gate
OFF run_match runs the byte-identical legacy shallow-hook combat instead of the
WINDOW passes.

We exercise the REAL shipped decision code: the tempo seat is the production
MurktideMatchAPL (its combat_priority_action is what production calls). The only
test-side scaffolding is the gated-combat SEQUENCE that run_match performs
inline (declare attackers -> [WINDOW 1] -> declare blockers -> [WINDOW 2] ->
resolve_combat -> move dead creatures), replicated here so we can hand-place
cards instead of running a full match with mulligans (design 4.1).

TEST 1 -- combat-trick PUMP line (WINDOW 2): a 2/2 attacker blocked by a 3/3;
          the tempo seat pumps it to 4/4 with Mutagenic Growth so it lives and
          kills the blocker. RED gate-OFF / GREEN gate-ON.
TEST 2 -- removal-makes-damage-go-through line (WINDOW 1): the attacker kills the
          defender's sole blocker pre-blocks so a 3/3 connects for 3. RED/GREEN.
TEST 3 -- bilateral APNAP (WINDOW 1, defender seat): the DEFENDER removes the
          lone attacker pre-damage; proves the window is APNAP, not attacker-
          only, and that combat math zeroes the removed attacker. RED/GREEN.

Results are emitted as a JSON block (PROOF_JSON_BEGIN/END) so the acceptance
harness can fold them into modelability_proofs/.
"""
import sys, os, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from engine.game_state import GameState
from engine.match_state import resolve_combat, safe_power, safe_toughness
import engine.match_engine as ME
from engine.match_engine import _instant_combat_enabled, _run_combat_window
from apl.match_apl import MatchAPL
from apl.murktide_match import MurktideMatchAPL


# ---------------------------------------------------------------------------
# APLs: the tempo seat is the REAL production MurktideMatchAPL (its
# combat_priority_action is the shipped decision code). The other seat is a
# plain MatchAPL that always passes (inherits the no-op combat_priority_action).
# ---------------------------------------------------------------------------

class PlainAPL(MatchAPL):
    name = "Plain (passes)"

    def keep(self, hand, mulligans, on_play):
        return True

    def bottom(self, hand, n):
        return hand[:n]

    def main_phase(self, gs):
        pass


def tempo_apl(gate_on):
    """Production MurktideMatchAPL with the R2 gate toggled (RED pre / GREEN post)."""
    apl = MurktideMatchAPL()
    apl.WANTS_INSTANT_COMBAT = gate_on
    return apl


# ---------------------------------------------------------------------------
# Card / state construction (hand-placed; no full match, no mulligans)
# ---------------------------------------------------------------------------

def creature(name, p, t):
    return Card(name=name, mana_cost="{1}{G}", cmc=2,
                type_line="Creature - Beast", power=str(p), toughness=str(t))


def mutagenic_growth():
    # Real +2/+2 free-via-Phyrexian pump; matches engine PUMP primitive (+2/+2)
    # and is in match_engine._FREE_PITCH_PUMP so it pays by pitch (no mana).
    return Card(name="Mutagenic Growth", mana_cost="", cmc=0,
                type_line="Instant",
                oracle_text="Target creature gets +2/+2 until end of turn.")


def unholy_heat():
    # InteractionType.REMOVAL in SPELL_DB; in MurktideMatchAPL.REMOVAL set.
    return Card(name="Unholy Heat", mana_cost="{R}", cmc=1,
                type_line="Instant",
                oracle_text="Unholy Heat deals damage to target creature.")


def make_gs(battlefield=None, hand=None, pool=None, life=20):
    gs = GameState([], on_play=True)
    gs.zones.battlefield = list(battlefield or [])
    gs.zones.hand = list(hand or [])
    gs.zones.graveyard = []
    gs.turn = 4
    gs.life = life
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


def apply_deaths(combat_result, active_gs, opp_gs):
    """Mirror run_match's post-combat death handling (match_engine ~L548)."""
    for dead in combat_result.attacker_deaths:
        if dead in active_gs.zones.battlefield:
            active_gs.zones.battlefield.remove(dead)
            active_gs.zones.graveyard.append(dead)
    for dead in combat_result.defender_deaths:
        if dead in opp_gs.zones.battlefield:
            opp_gs.zones.battlefield.remove(dead)
            opp_gs.zones.graveyard.append(dead)


def in_gy(gs, name):
    return any(c.name == name for c in gs.zones.graveyard)


# ---------------------------------------------------------------------------
# TEST 1 -- WINDOW 2 combat-trick PUMP (the headline differential)
# ---------------------------------------------------------------------------

def _run_test1_once(gate_on):
    """Attacker (tempo) controls a 2/2; defender a 3/3 that blocks it. The
    attacker holds Mutagenic Growth. Sequence mirrors run_match: blocks are
    declared, THEN WINDOW 2 (gate-dependent), THEN damage."""
    ME.reset_trick_count()
    atk_apl = tempo_apl(gate_on)
    def_apl = PlainAPL()

    bear = creature("Grizzly Bears", 2, 2)        # attacker, base 2/2
    blocker = creature("Hill Giant", 3, 3)        # defender, 3/3

    active = make_gs(battlefield=[bear], hand=[mutagenic_growth()])
    opp = make_gs(battlefield=[blocker])
    wire(active, atk_apl, opp, def_apl)

    attackers = [bear]
    # Blocks are declared BEFORE window 2 (the 3/3 blocks the 2/2).
    assignments = {id(bear): [blocker]}

    # --- gated WINDOW 2 (real production gate) ---
    if _instant_combat_enabled(active, opp):
        _run_combat_window(active, atk_apl, opp, def_apl, window=2)

    combat_result = resolve_combat(attackers, assignments, "a", None)
    apply_deaths(combat_result, active, opp)

    return {
        "gate_on": gate_on,
        "gate_seen": _instant_combat_enabled(active, opp),
        "tricks_cast": ME.TRICKS_CAST,
        "attacker_alive": bear in active.zones.battlefield,   # (a)
        "attacker_power": bear.effective_power(),
        "attacker_toughness": bear.effective_toughness(),
        "attacker_in_gy": in_gy(active, "Grizzly Bears"),
        "blocker_dead": blocker in opp.zones.graveyard,        # (b)
        "blocker_alive": blocker in opp.zones.battlefield,
        "pump_in_gy": in_gy(active, "Mutagenic Growth"),       # (d) cost paid
        "pump_left_hand": not any(c.name == "Mutagenic Growth"
                                  for c in active.zones.hand),
    }


def test1_pump_window2():
    pre = _run_test1_once(gate_on=False)
    post = _run_test1_once(gate_on=True)
    print("  TEST1 pre  (gate OFF):", json.dumps(pre))
    print("  TEST1 post (gate ON ):", json.dumps(post))

    # GREEN post: pump fired -> 4/4 attacker lives, 3/3 blocker dies.
    assert post["attacker_alive"], "post: attacker (4/4) should survive"
    assert post["attacker_power"] == 4 and post["attacker_toughness"] == 4, (
        f"post: attacker not 4/4 (got {post['attacker_power']}/"
        f"{post['attacker_toughness']})")
    assert post["blocker_dead"], "post: 3/3 blocker should be dead"
    assert post["tricks_cast"] > 0, "post: TRICKS_CAST must be > 0"
    assert post["pump_in_gy"] and post["pump_left_hand"], (
        "post: Mutagenic Growth must move hand -> graveyard (cost paid)")

    # RED pre: synchronous combat -> 2/2 attacker dies, 3/3 blocker lives.
    assert pre["attacker_in_gy"] and not pre["attacker_alive"], (
        "ABORT A: TEST1 not falsifying -- attacker survived pre-R2 (gate OFF)")
    assert pre["blocker_alive"] and not pre["blocker_dead"], (
        "ABORT A: TEST1 not falsifying -- blocker died pre-R2 (gate OFF)")
    assert pre["tricks_cast"] == 0, "ABORT A: a trick fired with the gate OFF"

    print("  TEST1 PASS (RED pre / GREEN post: pump flips attacker+blocker)")
    return {"pre": pre, "post": post}


# ---------------------------------------------------------------------------
# TEST 2 -- WINDOW 1 removal makes damage go through
# ---------------------------------------------------------------------------

def _run_test2_once(gate_on):
    """Attacker (tempo) swings a 3/3; defender controls exactly one 2/2 would-be
    blocker and is at 20. WINDOW 1 (gate-dependent) lets the attacker kill the
    2/2 pre-blocks; then the defender declares blocks on survivors; then damage."""
    ME.reset_trick_count()
    atk_apl = tempo_apl(gate_on)
    def_apl = PlainAPL()

    threat = creature("Watchwolf", 3, 3)          # attacker 3/3
    blocker = creature("Grizzly Bears", 2, 2)     # defender's sole 2/2

    active = make_gs(battlefield=[threat], hand=[unholy_heat()], pool={"R": 1})
    opp = make_gs(battlefield=[blocker], life=20)
    wire(active, atk_apl, opp, def_apl)

    attackers = [threat]

    # --- gated WINDOW 1 (before blocks) ---
    if _instant_combat_enabled(active, opp):
        _run_combat_window(active, atk_apl, opp, def_apl, window=1)
        attackers = [a for a in attackers if a in active.zones.battlefield]

    # Defender declares blocks on the creatures that survived the window. With a
    # live 2/2 it blocks the 3/3; with none it cannot block (attacker connects).
    def_creatures = [c for c in opp.zones.battlefield
                     if not c.is_land() and c.has(Tag.CREATURE)]
    if def_creatures and attackers:
        assignments = {id(attackers[0]): [def_creatures[0]]}
    else:
        assignments = {}

    combat_result = resolve_combat(attackers, assignments, "a", None)
    apply_deaths(combat_result, active, opp)
    defender_life_after = opp.life - combat_result.damage_to_defender

    return {
        "gate_on": gate_on,
        "tricks_cast": ME.TRICKS_CAST,
        "blocker_in_gy_before_blocks": in_gy(opp, "Grizzly Bears") and not def_creatures,
        "blocker_dead": blocker in opp.zones.graveyard,
        "attacker_unblocked": assignments == {},
        "damage_to_defender": combat_result.damage_to_defender,
        "defender_life_after": defender_life_after,            # (c)
    }


def test2_removal_window1():
    pre = _run_test2_once(gate_on=False)
    post = _run_test2_once(gate_on=True)
    print("  TEST2 pre  (gate OFF):", json.dumps(pre))
    print("  TEST2 post (gate ON ):", json.dumps(post))

    # GREEN post: 2/2 removed pre-blocks -> 3/3 unblocked -> 3 to face -> 17.
    assert post["blocker_dead"], "post: 2/2 blocker should be dead pre-blocks"
    assert post["attacker_unblocked"], "post: 3/3 should be unblocked"
    assert post["defender_life_after"] == 17, (
        f"post: defender life should be 17 (got {post['defender_life_after']})")
    assert post["tricks_cast"] > 0, "post: removal must register on TRICKS_CAST"

    # RED pre: 2/2 blocks the 3/3 -> 0 to face -> life stays 20.
    assert pre["defender_life_after"] == 20, (
        f"ABORT A: TEST2 not falsifying -- life moved pre-R2 "
        f"(got {pre['defender_life_after']})")
    assert not pre["attacker_unblocked"], (
        "ABORT A: TEST2 not falsifying -- attacker unblocked with the gate OFF")

    print("  TEST2 PASS (RED pre / GREEN post: removal opens 3 to face, 20 -> 17)")
    return {"pre": pre, "post": post}


# ---------------------------------------------------------------------------
# TEST 3 -- WINDOW 1 bilateral APNAP (defender removes the attacker)
# ---------------------------------------------------------------------------

def _run_test3_once(gate_on):
    """Attacker (PLAIN, passes) swings a lone 4/4 into an empty board; the
    DEFENDER is the tempo seat holding removal. WINDOW 1 is APNAP: active passes,
    defender removes the 4/4 pre-damage. Proves the window is not attacker-only."""
    ME.reset_trick_count()
    atk_apl = PlainAPL()
    def_apl = tempo_apl(gate_on)                  # the tempo seat is the DEFENDER

    threat = creature("Tarmogoyf", 4, 4)          # attacker's lone 4/4

    active = make_gs(battlefield=[threat])
    opp = make_gs(battlefield=[], hand=[unholy_heat()], pool={"R": 1}, life=20)
    wire(active, atk_apl, opp, def_apl)

    attackers = [threat]

    # --- gated WINDOW 1 (APNAP: active first, then defender) ---
    if _instant_combat_enabled(active, opp):
        _run_combat_window(active, atk_apl, opp, def_apl, window=1)
        attackers = [a for a in attackers if a in active.zones.battlefield]

    assignments = {}    # empty defender board -> no blocks
    combat_result = resolve_combat(attackers, assignments, "a", None)
    apply_deaths(combat_result, active, opp)
    defender_life_after = opp.life - combat_result.damage_to_defender

    return {
        "gate_on": gate_on,
        "tricks_cast": ME.TRICKS_CAST,
        "attacker_removed": threat in active.zones.graveyard,
        "attacker_still_attacking": threat in attackers,
        "removal_in_def_gy": in_gy(opp, "Unholy Heat"),
        "defender_life_after": defender_life_after,
    }


def test3_bilateral_apnap():
    pre = _run_test3_once(gate_on=False)
    post = _run_test3_once(gate_on=True)
    print("  TEST3 pre  (gate OFF):", json.dumps(pre))
    print("  TEST3 post (gate ON ):", json.dumps(post))

    # GREEN post: defender removes the 4/4 pre-damage -> life stays 20.
    assert post["attacker_removed"], "post: defender should remove the 4/4"
    assert not post["attacker_still_attacking"], "post: removed 4/4 still attacking"
    assert post["defender_life_after"] == 20, (
        f"post: defender life should be 20 (got {post['defender_life_after']})")
    assert post["removal_in_def_gy"], "post: defender's removal should be in its gy"
    assert post["tricks_cast"] > 0, "post: defender response must register"

    # RED pre: unblocked 4/4 -> defender life 16.
    assert pre["defender_life_after"] == 16, (
        f"ABORT A: TEST3 not falsifying -- defender life {pre['defender_life_after']} "
        "(expected 16 with gate OFF)")
    assert not pre["attacker_removed"], (
        "ABORT A: TEST3 not falsifying -- attacker removed with the gate OFF")

    print("  TEST3 PASS (RED pre / GREEN post: defender APNAP removal saves 4 life)")
    return {"pre": pre, "post": post}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    print("R2 instant-speed combat PROOF (differential RED-pre / GREEN-post)")
    results = {}
    ok = True
    for name, fn in [("test1_pump_window2", test1_pump_window2),
                     ("test2_removal_window1", test2_removal_window1),
                     ("test3_bilateral_apnap", test3_bilateral_apnap)]:
        try:
            results[name] = fn()
        except AssertionError as e:
            ok = False
            print(f"  {name} FAIL: {e}")

    print()
    if ok:
        print("ALL R2 PROOF TESTS PASS")
    else:
        print("R2 PROOF TESTS FAILED")

    print("PROOF_JSON_BEGIN")
    print(json.dumps(results, indent=2))
    print("PROOF_JSON_END")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
