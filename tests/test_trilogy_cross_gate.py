"""test_trilogy_cross_gate.py -- AIRTIGHT cross-gate composition proof.

The trilogy R1 (on-stack priority counters), R2 (instant-speed combat windows),
and R5 (planeswalker loyalty in match mode) each shipped behind its own
capability gate (WANTS_PRIORITY_STACK / WANTS_INSTANT_COMBAT / WANTS_PW_LOYALTY).
Each was proven IN ISOLATION by its own spike suite. This test proves the
NEVER-BEFORE-TESTED surface: that the three gated subsystems COMPOSE -- enabled
together on real APLs they run full matches with NO crash, DETERMINISTICALLY,
and each subsystem's instrumentation still FIRES (none suppresses or corrupts
another).

Run:  PYTHONIOENCODING=utf-8 python tests/test_trilogy_cross_gate.py
ASCII-only, plain-assert, exit 0 on pass / 1 on failure. Conventions match
tests/test_r1_control_exercises.py (real match_runner path, n_workers=1 so the
in-process module-global instrumentation counters are visible).

STRUCTURAL FACT (honest, not a workaround): a Magic match has exactly TWO seats,
but the three capabilities live in THREE different archetypes -- R1 counters come
only from the AwareMatchAPL priority loop, R2 tricks only from a
combat_priority_action APL (Murktide), R5 loyalty only from a deck that fields
planeswalkers (Eldrazi Tron / Karn). So "all three firing from real registered
archetypes in one 2-seat game" is impossible by construction. SUBTEST A closes
that gap with a single seat that genuinely carries BOTH R1 and R2 (a real
composition of two shipped decision modules -- AwareMatchAPL.priority_action +
MurktideMatchAPL.combat_priority_action -- NOT a hand-rolled stub) facing a real
Karn deck, so all three gated subsystems fire in ONE all-gates-ON match set.
SUBTESTs B and C corroborate with pairs of fully-registered archetypes.

In EVERY subtest ALL THREE gates are forced ON on BOTH seats, so the engine is
running with the entire trilogy live; the matchup just determines which counters
get a chance to tick.
"""
import sys, os, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_matchup_data import load_deck_and_apl
from apl import get_match_apl
from apl.aware_match_apl import AwareMatchAPL
from apl.match_apl import MatchAPL
from apl.murktide_match import MurktideMatchAPL
from engine.match_runner import run_match_set, TwoPlayerGameState, _resolve_combat
from engine.match_state import safe_power
from engine.keywords import tag_keywords
from engine.stack import classify_card
from data.card import Card, Tag
import engine.priority_stack as ps
import engine.match_engine as ME
import engine.planeswalkers as pw

FORMAT = "modern"
N = 40
SEED = 42

RESULTS = {}


class R1R2Hybrid(AwareMatchAPL, MurktideMatchAPL):
    """One seat that genuinely carries BOTH gated decision modules.

    MRO: R1R2Hybrid -> AwareMatchAPL -> MurktideMatchAPL -> MatchAPL.
      * priority_action          (R1, on-stack counters)  <- AwareMatchAPL
      * combat_priority_action   (R2, instant combat)      <- MurktideMatchAPL
    Both are the REAL shipped methods, not re-implementations. Run on the Dimir
    Murktide deck (Counterspell/Spell Snare/Spell Pierce for R1; the removal/pump
    combat_priority_action keys for R2), all three gates ON.
    """
    name = "R1R2 Hybrid (counter + combat trick)"
    WANTS_PRIORITY_STACK = True
    WANTS_INSTANT_COMBAT = True
    WANTS_PW_LOYALTY = True


def _force_all_gates(apl):
    apl.WANTS_PRIORITY_STACK = True
    apl.WANTS_INSTANT_COMBAT = True
    apl.WANTS_PW_LOYALTY = True
    return apl


def _snapshot():
    """All three subsystems' in-process instrumentation + nothing else."""
    return {
        "counters_cast": ps.COUNTERS_CAST,     # R1
        "tricks_cast": ME.TRICKS_CAST,         # R2
        "pw_activations": pw.PW_ACTIVATIONS,   # R5
        "pw_ultimates": pw.PW_ULTIMATES,       # R5
        "pw_combat_deaths": pw.PW_COMBAT_DEATHS,  # R5
    }


def _run_set(make_apl_a, deck_a, deck_b_name, seed):
    """Run one all-gates-ON match set; return (instrumentation_snapshot, wr).

    Resets ALL THREE module-global counters first so the snapshot reflects ONLY
    this run. n_workers=1 keeps the counters in-process (a ProcessPool would hide
    them in child processes)."""
    deck_b, _, _ = load_deck_and_apl(deck_b_name, FORMAT)
    apl_b = _force_all_gates(get_match_apl(deck_b_name))
    ps.reset_fire_count()
    ME.reset_trick_count()
    pw.reset_fire_count()
    res = run_match_set(make_apl_a(), deck_a, apl_b, deck_b,
                        n=N, seed=seed, mix_play_draw=True, n_workers=1)
    snap = _snapshot()
    snap["wr"] = round(res.win_pct(), 4)
    return snap


def _assert(cond, msg):
    print(("  ok: " if cond else "  FAIL: ") + msg)
    if not cond:
        sys.exit(1)


# ---------------------------------------------------------------------------
# SUBTEST A -- the centerpiece: ALL THREE gated subsystems fire in ONE
# all-gates-ON match set, with no crash, deterministically.
#   seat A = R1R2Hybrid on the Dimir Murktide deck (counters R1 + tricks R2)
#   seat B = Eldrazi Tron (Karn -> loyalty R5), all gates forced
# ---------------------------------------------------------------------------
def subtest_a_all_three():
    print("SUBTEST A: R1 + R2 + R5 all fire in one all-gates-ON match set")
    deck_a, _, _ = load_deck_and_apl("Murktide", FORMAT)  # dimir_oculus deck

    run1 = _run_set(lambda: R1R2Hybrid(), deck_a, "Eldrazi Tron", SEED)
    run2 = _run_set(lambda: R1R2Hybrid(), deck_a, "Eldrazi Tron", SEED)
    RESULTS["subtest_a"] = {"run1": run1, "run2": run2}
    print("  run1:", json.dumps(run1))
    print("  run2:", json.dumps(run2))

    # No crash: reaching here over N*2 games means run_match_set never raised.
    _assert(run1["counters_cast"] > 0, "R1 fired (on-stack counters) with all gates ON")
    _assert(run1["tricks_cast"] > 0, "R2 fired (instant-speed combat tricks) with all gates ON")
    _assert(run1["pw_activations"] > 0, "R5 fired (planeswalker activations) with all gates ON")
    # Determinism: same seed twice -> byte-identical instrumentation AND WR.
    _assert(run1 == run2, "deterministic: same seed twice -> identical counters + WR")
    print("  PASS SUBTEST A (R1+R2+R5 coexist, no crash, deterministic)\n")


# ---------------------------------------------------------------------------
# SUBTEST B -- task example 2 with TWO real registered archetypes: a
# planeswalker ticks/ultimates (R5) while the opponent holds counter mana (R1).
#   seat A = UW Control (real R1 counter loop)
#   seat B = Eldrazi Tron (real Karn loyalty/ultimate)
# ---------------------------------------------------------------------------
def subtest_b_r1_plus_r5():
    print("SUBTEST B: R5 PW ticks/ultimates while R1 opponent holds counters "
          "(UW Control vs Eldrazi Tron, both real archetypes)")
    deck_a, _, _ = load_deck_and_apl("UW Control", FORMAT)

    run1 = _run_set(lambda: _force_all_gates(get_match_apl("UW Control")),
                    deck_a, "Eldrazi Tron", SEED)
    run2 = _run_set(lambda: _force_all_gates(get_match_apl("UW Control")),
                    deck_a, "Eldrazi Tron", SEED)
    RESULTS["subtest_b"] = {"run1": run1, "run2": run2}
    print("  run1:", json.dumps(run1))
    print("  run2:", json.dumps(run2))

    _assert(run1["counters_cast"] > 0, "R1 fired (UW Control countered on the stack)")
    _assert(run1["pw_activations"] > 0, "R5 fired (Karn loyalty activations)")
    _assert(run1["pw_ultimates"] > 0, "R5 ultimate fired at least once alongside R1")
    _assert(run1 == run2, "deterministic: same seed twice -> identical counters + WR")
    print("  PASS SUBTEST B (R1 + R5 compose in real match play)\n")


# ---------------------------------------------------------------------------
# SUBTEST C -- R2 + R5 with TWO real registered archetypes: instant-speed combat
# tricks fire while a planeswalker is live.
#   seat A = Eldrazi Tron (real Karn loyalty)
#   seat B = Murktide (real instant-combat tricks)
# ---------------------------------------------------------------------------
def subtest_c_r2_plus_r5():
    print("SUBTEST C: R2 combat tricks fire while R5 planeswalker is live "
          "(Eldrazi Tron vs Murktide, both real archetypes)")
    deck_a, _, _ = load_deck_and_apl("Eldrazi Tron", FORMAT)

    run1 = _run_set(lambda: _force_all_gates(get_match_apl("Eldrazi Tron")),
                    deck_a, "Murktide", SEED)
    run2 = _run_set(lambda: _force_all_gates(get_match_apl("Eldrazi Tron")),
                    deck_a, "Murktide", SEED)
    RESULTS["subtest_c"] = {"run1": run1, "run2": run2}
    print("  run1:", json.dumps(run1))
    print("  run2:", json.dumps(run2))

    _assert(run1["tricks_cast"] > 0, "R2 fired (Murktide instant-speed combat tricks)")
    _assert(run1["pw_activations"] > 0, "R5 fired (Eldrazi Tron Karn activations)")
    _assert(run1 == run2, "deterministic: same seed twice -> identical counters + WR")
    print("  PASS SUBTEST C (R2 + R5 compose in real match play)\n")


# ---------------------------------------------------------------------------
# SUBTEST D -- the NOVEL SURFACE this merge authored: the R2-WINDOW-2-before-R5-
# pw_assignment ordering inside match_runner._resolve_combat (merge conflict B).
# Subtests A-C prove the gates COMPOSE broadly but NEVER trigger this exact
# surface: a defender-side window-2 removal that prunes an attacker BEFORE R5
# decides which unblocked attackers to divert at a planeswalker. The failure
# mode of a reversed ordering is SILENT (no crash), so it must be asserted
# directly. Driven in-vitro through the real _resolve_combat (same harness as
# tests/test_r5_planeswalker_loyalty.py) -- combat-only, no R1 view-wiring, so
# no fragility.
#
# Scenario (lethality-flip, the only shape that discriminates the ordering):
#   attacker A: BigOgre 18/1 + SmallBear 2/2, both unblocked.
#   defender B: Karn (loyalty 3), life 20, holds Unholy Heat (window-2 removal).
#   B's combat_priority_action kills the 18-power BigOgre in WINDOW 2.
#
# R5's divert gate is "divert only if the unblocked attack is NOT lethal to the
# face" (total_unblocked < defender_life). 18 + 2 == 20 == life -> looks LETHAL;
# 2 alone < 20 -> NOT lethal. So the diversion decision hinges entirely on
# whether total_unblocked is measured BEFORE or AFTER the window-2 kill.
#   correct order (W2 then pw_assignment): big pruned -> total 2 < 20 -> SmallBear
#       diverted to Karn -> Karn 3-2=1, face damage 0.
#   reversed order (pw_assignment then W2): total 20 not < 20 -> divert nothing ->
#       SmallBear hits the face for 2 -> Karn unchanged at 3, face damage 2.
# The SUPPRESSED-removal control pins the lethal branch: with both attackers
# alive total IS 20 -> nothing diverted -> 20 to the face, Karn 3. Observing
# Karn==1 / face==0 in the WITH-removal run is therefore only explicable if the
# window-2 prune happened FIRST -- a direct proof of the merged ordering.
# ---------------------------------------------------------------------------

class _PlainAttacker(MatchAPL):
    name = "Plain attacker (passes)"
    def keep(self, hand, mulligans, on_play): return True
    def bottom(self, hand, n): return []
    def main_phase(self, gs): return None


class _DefenderWindow2Removal(MatchAPL):
    """Defender that opts into BOTH R2 and R5 and, in WINDOW 2, removes the
    biggest opposing attacker (real engine removal path)."""
    name = "Defender (window-2 removal)"
    WANTS_INSTANT_COMBAT = True
    WANTS_PW_LOYALTY = True

    def __init__(self, suppress=False):
        self.suppress = suppress

    def keep(self, hand, mulligans, on_play): return True
    def bottom(self, hand, n): return []
    def main_phase(self, gs): return None

    def combat_priority_action(self, my_gs, their_gs, stack, window):
        if self.suppress or window != 2 or their_gs is None or my_gs is None:
            return None
        removal = next((c for c in my_gs.zones.hand if c.name == "Unholy Heat"), None)
        if removal is None:
            return None
        attackers = [c for c in their_gs.zones.battlefield
                     if not c.is_land() and c.has(Tag.CREATURE)]
        if not attackers:
            return None
        return (removal, max(attackers, key=safe_power))


def _cg_pw(name, loyalty):
    c = Card(name=name, mana_cost="{7}", cmc=7,
             type_line="Legendary Planeswalker - " + name,
             power=None, toughness=None, colors=[])
    tag_keywords(c)
    c.loyalty = loyalty
    return c


def _cg_creature(name, p, t):
    c = Card(name=name, mana_cost="{2}", cmc=3, type_line="Creature - Test",
             power=str(p), toughness=str(t), colors=["G"])
    tag_keywords(c)
    c.summoning_sickness = False
    return c


def _cg_mountain():
    c = Card(name="Mountain", mana_cost="", cmc=0,
             type_line="Basic Land - Mountain", power=None, toughness=None, colors=[])
    tag_keywords(c)
    return c


def _cg_unholy_heat():
    c = Card(name="Unholy Heat", mana_cost="{R}", cmc=1, type_line="Instant",
             oracle_text="Unholy Heat deals damage to target creature.")
    tag_keywords(c)
    return c


def _run_ordering_scenario(suppress):
    pw.reset_fire_count()
    gs = TwoPlayerGameState([], [], on_play=True, seed=SEED)
    gs.apl_a = _PlainAttacker()
    gs.apl_b = _DefenderWindow2Removal(suppress=suppress)
    gs.life_a, gs.life_b = 20, 20
    big = _cg_creature("BigOgre", 18, 1)
    small = _cg_creature("SmallBear", 2, 2)
    gs.bf_a.append(big)
    gs.bf_a.append(small)
    karn = _cg_pw("Karn Liberated", 3)
    gs.bf_b.append(karn)
    gs.bf_b.append(_cg_mountain())
    gs.hand_b.append(_cg_unholy_heat())
    face_dmg, _alost, _dlost, _llg, _dllg, _hit = _resolve_combat(gs, "a")
    return {
        "face_dmg": face_dmg,
        "karn_loyalty": karn.loyalty,
        "karn_alive": karn in gs.bf_b,
        "big_in_gy": big in gs.gy_a,
        "small_alive": small in gs.bf_a,
    }


def subtest_d_window2_before_pw_assignment():
    print("SUBTEST D: R2 window-2 removal prunes an attacker BEFORE R5 "
          "pw_assignment (the ordering this merge authored)")
    # Assert the real classification so the test fails loudly if Unholy Heat ever
    # stops being engine REMOVAL (the whole scenario depends on it killing big).
    _assert(classify_card(_cg_unholy_heat()).name == "REMOVAL",
            "Unholy Heat classifies as engine REMOVAL (precondition)")

    with_removal = _run_ordering_scenario(suppress=False)
    with_removal_2 = _run_ordering_scenario(suppress=False)
    control = _run_ordering_scenario(suppress=True)
    RESULTS["subtest_d"] = {"with_removal": with_removal,
                            "suppressed_control": control}
    print("  WITH window-2 removal:", json.dumps(with_removal))
    print("  SUPPRESSED control   :", json.dumps(control))

    # Window-2 removal actually fired and killed the big attacker.
    _assert(with_removal["big_in_gy"], "window-2 removal killed BigOgre (R2 fired)")
    _assert(with_removal["small_alive"], "SmallBear survived (not removed)")
    # GREEN (correct ordering): post-prune total 2 < 20 -> SmallBear diverted to
    # Karn -> loyalty 3 - 2 = 1, walker survives, ZERO face damage.
    _assert(with_removal["karn_loyalty"] == 1,
            "Karn loyalty 3 -> 1 (SmallBear diverted using POST-window-2 state)")
    _assert(with_removal["karn_alive"], "Karn survived (loyalty > 0)")
    _assert(with_removal["face_dmg"] == 0,
            "zero face damage (the only unblocked attacker went at the walker)")
    # Control pins the lethal branch the reversed ordering would have taken.
    _assert(not control["big_in_gy"], "control: BigOgre alive (removal suppressed)")
    _assert(control["face_dmg"] == 20 and control["karn_loyalty"] == 3,
            "control: total 20 == life -> lethal -> nothing diverted, 20 to face, "
            "Karn untouched")
    # Discriminator: WITH-removal diverges from the control's lethal branch ONLY
    # because total_unblocked was recomputed after the window-2 prune. A reversed
    # ordering would reproduce the control's divert decision (Karn 3, face 2).
    _assert(with_removal["karn_loyalty"] != control["karn_loyalty"]
            and with_removal["face_dmg"] != control["face_dmg"],
            "ordering discriminator: post-prune divert differs from pre-prune lethal")
    # Determinism on the novel surface.
    _assert(with_removal == with_removal_2,
            "deterministic: same scenario twice -> identical")
    print("  PASS SUBTEST D (window-2 prune precedes pw_assignment; "
          "divert reads post-window-2 state)\n")


if __name__ == "__main__":
    subtest_a_all_three()
    subtest_b_r1_plus_r5()
    subtest_c_r2_plus_r5()
    subtest_d_window2_before_pw_assignment()
    print("ALL TRILOGY CROSS-GATE TESTS PASS")
    print("RESULTS_JSON " + json.dumps(RESULTS))
    sys.exit(0)
