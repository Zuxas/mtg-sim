"""test_r1_control_exercises.py -- the narrowed-R1 EXERCISE proof.

After narrowing, the WANTS_PRIORITY_STACK opt-in lives ONLY on the control
subclass (apl/uw_control_modern_match.py); the base AwareMatchAPL ships False, so
the other 37 Standard match decks never reach engine.priority_stack. This test
proves the OTHER half of the claim: the registered UW Control APL DOES fire the
real on-stack priority loop in actual match play (not just in the in-vitro
proof-test harness).

Method: run a real N-game match set (engine.match_runner.run_match_set, single
process so the in-process fire counter is visible) of UW Control vs a
threat-dense creature opponent, with engine.priority_stack.COUNTERS_CAST
instrumented. That counter only ever increments inside run_priority_stack when a
counter is actually placed on the stack -- the legacy gate-OFF path never reaches
that module -- so a NONZERO count is direct evidence that R1 fired in real games.

Run:  PYTHONIOENCODING=utf-8 python tests/test_r1_control_exercises.py
"""
import sys, os, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_matchup_data import load_deck_and_apl
from apl import get_match_apl
from engine.match_runner import run_match_set
import engine.priority_stack as ps


OUR_DECK = "UW Control"
OPP_DECK = "Boros Energy"   # threat-dense creature deck -> many counterable casts
FORMAT = "modern"
N = 60
SEED = 42


def main():
    our_main, _our_side, _ = load_deck_and_apl(OUR_DECK, FORMAT)
    opp_main, _opp_side, _ = load_deck_and_apl(OPP_DECK, FORMAT)
    our_mapl = get_match_apl(OUR_DECK)
    opp_mapl = get_match_apl(OPP_DECK)

    assert our_main, "could not load UW Control mainboard"
    assert opp_main, "could not load opponent mainboard"
    assert our_mapl is not None, "could not load UW Control MatchAPL"
    assert opp_mapl is not None, "could not load opponent MatchAPL"

    # Confirm the gate is opted-in ONLY on the control side (the narrowing).
    our_gate = getattr(type(our_mapl), "WANTS_PRIORITY_STACK", False)
    opp_gate = getattr(type(opp_mapl), "WANTS_PRIORITY_STACK", False)
    print(f"  our_apl={type(our_mapl).__name__} WANTS_PRIORITY_STACK={our_gate}")
    print(f"  opp_apl={type(opp_mapl).__name__} WANTS_PRIORITY_STACK={opp_gate}")
    assert our_gate is True, "UW Control APL does not opt into R1 (gate not set)"
    assert opp_gate is False, "opponent unexpectedly opts into R1 (narrowing leak)"

    ps.reset_fire_count()
    res = run_match_set(our_mapl, our_main, opp_mapl, opp_main,
                        n=N, seed=SEED, mix_play_draw=True, n_workers=1)
    fired = ps.COUNTERS_CAST
    wr = res.win_pct()

    obs = {
        "our_deck": OUR_DECK,
        "opp_deck": OPP_DECK,
        "n": N,
        "seed": SEED,
        "priority_stack_counters_cast": fired,
        "g1_win_pct": round(wr, 1),
    }
    print("  EXERCISE:", json.dumps(obs))
    assert fired > 0, (
        "ABORT: R1 never fired in real match play (COUNTERS_CAST=0). "
        "The narrowed control APL is wired but never countered on the stack -- "
        "this would be a tuning/wiring finding, not a pass.")
    print(f"  PASS -- R1 fired {fired} times on the stack across {N} real games "
          f"(UW Control exercises the priority loop in match play)")

    print("PROOF_JSON_BEGIN")
    print(json.dumps(obs, indent=2))
    print("PROOF_JSON_END")
    print("R1 CONTROL EXERCISE TEST PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
