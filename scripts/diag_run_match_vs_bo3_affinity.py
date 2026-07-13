"""scripts/diag_run_match_vs_bo3_affinity.py

Characterize the bo3-run_fair-vs-run_match divergence (harness IMPERFECTION
bo3-run_fair-vs-run_match-divergence). Runs Boros-Low-Curve vs Affinity through
BOTH match engines with the SAME match APLs / decks / seed / play-draw mix, so the
only variable is the engine implementation:

  - run_bo3_set   -> engine.bo3_match / MatchGameState   (the _run_fair field cell)
  - run_match_set -> engine.match_runner / TwoPlayerGameState (the wpb4 63.0 path)

Metric is single-game WR (bo3 g1 vs run_match single-game), never the bo3 match WR.
Determinism: run with PYTHONHASHSEED=0 and n_workers=1 (wpb4 warns the match path
has cross-process set-ordering noise).

Usage:  PYTHONHASHSEED=0 python scripts/diag_run_match_vs_bo3_affinity.py [n] [seed]
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

OUR = "borosenergylowcurve"
FMT = "modern"

def main():
    n    = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    OPP  = sys.argv[3] if len(sys.argv) > 3 else "affinity"

    from generate_matchup_data import load_deck_and_apl
    from apl import get_match_apl
    from engine.bo3_match import run_bo3_set
    from engine.match_runner import run_match_set

    our_main, our_side, _our_gold = load_deck_and_apl(OUR, FMT)
    opp_main, opp_side, _opp_gold = load_deck_and_apl(OPP, FMT)
    assert our_main and opp_main, "deck load failed"

    # SAME match APLs on BOTH engines (hold APL + build constant).
    def mapls():
        return get_match_apl(OUR), get_match_apl(OPP)

    our_sb = {}
    for c in (our_side or []):
        our_sb[c.name] = our_sb.get(c.name, 0) + 1
    opp_sb = {}
    for c in (opp_side or []):
        opp_sb[c.name] = opp_sb.get(c.name, 0) + 1

    print(f"[diag] {OUR} vs {OPP}  n={n} seed={seed} PYTHONHASHSEED={os.environ.get('PYTHONHASHSEED')}")

    # --- Engine A: MatchGameState via run_bo3_set (the _run_fair field cell) ---
    a1, a2 = mapls()
    bo3 = run_bo3_set(a1, our_main, our_sb, a2, opp_main, opp_sb,
                      sb_plan_a=([], []), sb_plan_b=None,
                      n=n, mix_play_draw=True, seed=seed, n_workers=1)
    bo3_g1 = bo3.g1_wr_a
    bo3_match = bo3.match_wr_a()

    # --- Engine B: TwoPlayerGameState via run_match_set (the wpb4 run_match path) ---
    b1, b2 = mapls()
    rm = run_match_set(b1, our_main, b2, opp_main,
                       n=n, seed=seed, mix_play_draw=True, n_workers=1)
    rm_wr = rm.win_pct()

    # run_match is single-game; convert to Bo3 match-level (p^2*(3-2p)) so it can be
    # compared to MATCH-level paper anchors apples-to-apples (advisor/fable metric fix).
    p = rm_wr / 100.0
    rm_match = 100.0 * (p * p * (3 - 2 * p))

    print("=" * 60)
    print(f"  [ENGINE DIVERGENCE, single-game g1]  bo3_g1 {bo3_g1:.1f}%  vs  run_match {rm_wr:.1f}%"
          f"   (delta {rm_wr - bo3_g1:+.1f}pp)")
    print(f"  [MATCH-LEVEL, vs paper]  bo3_match {bo3_match:.1f}%  vs  run_match->Bo3 {rm_match:.1f}%")
    print("=" * 60)

if __name__ == "__main__":
    main()
