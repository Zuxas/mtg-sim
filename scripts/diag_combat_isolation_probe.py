"""scripts/diag_combat_isolation_probe.py

Bounded combat-isolation probe (bob-20260713-103202-7918, IMPERFECTION
bo3-run_fair-vs-run_match-divergence). NON-DESTRUCTIVE: runtime monkeypatch only,
no engine edit. One degenerate lever at a time to bound COMBAT's share of the
field-read's Affinity under-rate (bo3 match 47.8% vs paper 72.7%):

  baseline  : Affinity blocks + attacks via its real APL (the field-read)
  no-block  : Affinity.declare_blockers -> {} (never blocks)  -> does Boros rise toward 72.7?
  attack-all: Affinity.declare_attackers -> all non-sick creatures -> does Boros change?

If no-block moves bo3_match a lot toward paper, Affinity's APL BLOCKING is the mechanism.
Cheap, nothing to get wrong (upper-bound levers), settles combat's attribution share.

Usage: PYTHONHASHSEED=0 python scripts/diag_combat_isolation_probe.py [n] [seed]
"""
import sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT))

OUR, OPP, FMT, N_DEFAULT = "borosenergylowcurve", "affinity", "modern", 3000

def _run(label, patch_blockers=False, patch_attackers=False, n=3000, seed=42):
    from generate_matchup_data import load_deck_and_apl
    from apl import get_match_apl
    from engine.bo3_match import run_bo3_set
    import apl.affinity_match as am

    orig_b = am.IzzetAffinityMatchAPL.declare_blockers
    orig_a = getattr(am.IzzetAffinityMatchAPL, "declare_attackers", None)
    try:
        if patch_blockers:
            am.IzzetAffinityMatchAPL.declare_blockers = lambda self, *a, **k: {}
        if patch_attackers and orig_a is not None:
            # attack-all: every non-summoning-sick creature on the affinity board
            def _attack_all(self, gs, opp_gs, *a, **k):
                bf = getattr(gs, "zones", None)
                cards = gs.zones.battlefield if bf else []
                return [c for c in cards
                        if getattr(c, "tags", None) and not getattr(c, "summoning_sickness", False)
                        and not getattr(c, "tapped", False) and "Creature" in (c.type_line or "")]
            am.IzzetAffinityMatchAPL.declare_attackers = _attack_all

        our_main, our_side, _ = load_deck_and_apl(OUR, FMT)
        opp_main, opp_side, _ = load_deck_and_apl(OPP, FMT)
        our_sb = {}
        for c in (our_side or []): our_sb[c.name] = our_sb.get(c.name, 0) + 1
        opp_sb = {}
        for c in (opp_side or []): opp_sb[c.name] = opp_sb.get(c.name, 0) + 1
        bo3 = run_bo3_set(get_match_apl(OUR), our_main, our_sb,
                          get_match_apl(OPP), opp_main, opp_sb,
                          sb_plan_a=([], []), sb_plan_b=None,
                          n=n, mix_play_draw=True, seed=seed, n_workers=1)
        print(f"  {label:22} bo3_match={bo3.match_wr_a():.1f}%  g1={bo3.g1_wr_a:.1f}%")
        return bo3.match_wr_a()
    finally:
        am.IzzetAffinityMatchAPL.declare_blockers = orig_b
        if orig_a is not None:
            am.IzzetAffinityMatchAPL.declare_attackers = orig_a

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else N_DEFAULT
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    print(f"[isolation probe] {OUR} vs {OPP}  n={n} seed={seed}  (paper 72.7%, run_match->Bo3 ~78%)")
    base = _run("baseline (real APL)", n=n, seed=seed)
    nob  = _run("Affinity NO-BLOCK", patch_blockers=True, n=n, seed=seed)
    print(f"  => no-block moved bo3_match {nob - base:+.1f}pp (toward paper 72.7 if positive)")

if __name__ == "__main__":
    main()
