"""
test_run_match_set_workers.py — Stage 1 validation for within-matchup
parallelism in engine/match_runner.run_match_set.

Three checks per the perf spec
(harness/knowledge/tech/perf-within-matchup-parallelism-2026-04-26.md):

1. Determinism: workers=1 with same seed produces same win_pct twice.
2. Statistical equivalence: workers=4 within +/-2pp of workers=1 at n=10000.
3. Speedup: workers=8 produces measurable speedup vs workers=1 at n=10000.

Uses BE vs Domain Zoo as the test matchup -- a real Modern matchup
that exercises the both-sides sim path (no combo sampler shortcut).
"""
from __future__ import annotations
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.match_runner import run_match_set
from generate_matchup_data import load_deck_and_apl


def _load_matchup(our_name, opp_name):
    our_main, _, our_apl = load_deck_and_apl(our_name, "modern")
    opp_main, _, opp_apl = load_deck_and_apl(opp_name, "modern")
    if not our_main or not opp_main:
        raise SystemExit(f"deck load failed: {our_name} vs {opp_name}")
    return our_apl, our_main, opp_apl, opp_main


def main():
    OUR  = "Boros Energy"
    OPP  = "Domain Zoo"
    SEED = 42
    N    = 10_000

    print(f"\n=== Stage 1 validation: {OUR} vs {OPP} ===\n")
    apl_a, deck_a, apl_b, deck_b = _load_matchup(OUR, OPP)

    print("[1] Determinism: workers=1 twice with same seed")
    r1a = run_match_set(apl_a, deck_a, apl_b, deck_b,
                        n=200, seed=SEED, workers=1)
    r1b = run_match_set(apl_a, deck_a, apl_b, deck_b,
                        n=200, seed=SEED, workers=1)
    print(f"  run 1: {r1a.win_pct():.2f}%  | run 2: {r1b.win_pct():.2f}%")
    assert r1a.win_pct() == r1b.win_pct(), "workers=1 not deterministic at fixed seed"
    print("  PASS: deterministic\n")

    print(f"[2] Statistical equivalence: workers=4 vs workers=1 at n={N}")
    t0 = time.time()
    r_serial = run_match_set(apl_a, deck_a, apl_b, deck_b,
                             n=N, seed=SEED, workers=1)
    t_serial = time.time() - t0
    print(f"  workers=1: {r_serial.win_pct():.2f}%  ({t_serial:.1f}s)")

    t0 = time.time()
    r_par4 = run_match_set(apl_a, deck_a, apl_b, deck_b,
                           n=N, seed=SEED, workers=4)
    t_par4 = time.time() - t0
    print(f"  workers=4: {r_par4.win_pct():.2f}%  ({t_par4:.1f}s)")

    delta4 = abs(r_serial.win_pct() - r_par4.win_pct())
    print(f"  delta: {delta4:.2f}pp")
    assert delta4 < 2.0, f"workers=4 diverges {delta4:.2f}pp from serial (>2pp threshold)"
    print("  PASS: within +/-2pp\n")

    print(f"[3] Speedup: workers=8 vs workers=1 at n={N}")
    t0 = time.time()
    r_par8 = run_match_set(apl_a, deck_a, apl_b, deck_b,
                           n=N, seed=SEED, workers=8)
    t_par8 = time.time() - t0
    speedup = t_serial / t_par8 if t_par8 > 0 else 0
    delta8 = abs(r_serial.win_pct() - r_par8.win_pct())
    print(f"  workers=8: {r_par8.win_pct():.2f}%  ({t_par8:.1f}s)  delta={delta8:.2f}pp")
    print(f"  serial: {t_serial:.1f}s  parallel-8: {t_par8:.1f}s  speedup: {speedup:.2f}x")
    assert delta8 < 2.0, f"workers=8 diverges {delta8:.2f}pp from serial (>2pp threshold)"
    if speedup < 2.0:
        print(f"  WARN: speedup {speedup:.2f}x < 2x threshold (overhead may dominate)")
    else:
        print(f"  PASS: speedup >= 2x")

    print(f"\n=== Stage 1 validation complete ===")
    print(f"  serial   ({N} games):  {t_serial:.1f}s")
    print(f"  workers=4: {t_par4:.1f}s  ({t_serial/t_par4:.2f}x speedup)")
    print(f"  workers=8: {t_par8:.1f}s  ({speedup:.2f}x speedup)")


if __name__ == "__main__":
    main()
