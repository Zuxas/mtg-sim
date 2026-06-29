"""
apl_quality.eval.py -- a REAL evalite-shaped eval over eval_harness.py.

Unlike example_apl.eval.py (which feeds the MonteCarloScorer pre-baked result
dicts), this eval runs the ACTUAL Monte Carlo sim (MonteCarloScorer.run_matchup_
task -> run_matchup._run_fair -> real two-player match-APL Bo3) on real decks. It
validates the eval harness end-to-end on real data.

What it scores
--------------
Five "our" APLs, each played against the SAME couple of Modern field opponents:

  field-gap APLs (new, 2026-06-28, "WF-1 / confidence medium"):
    - temurprowess     (decks/temur_prowess_standard.txt)
    - sultaimidrange   (decks/sultai_midrange_modern.txt)
    - grixismidrange   (decks/dimir_murktide_modern.txt)
  canonical anchors:
    - borosenergy      (decks/boros_energy_modern.txt)
    - izzetprowess     ("prowess" -> decks/izzet_prowess_modern.txt)

  field opponents (both have real MATCH_APLs + deck files, so the matchup routes
  through run_matchup Path A = real Bo3, g1_source='bo3'):
    - amulettitan
    - yawgmoth

That is 5 x 2 = 10 EvalCases. Each case id is "<apl>_vs_<opp>" so the per-APL
table in the report can be reconstructed by grouping case rows on the prefix
(evalite() itself only reports ONE global mean -- per-APL aggregation is done
here / in the report, not by the runner).

Scorer
------
ONLY the MonteCarloScorer (winrate_over_N) is active. It is a pure function of
the run_matchup result dict and needs NO live model. The gemma4 (Ollama) and
Anthropic-SDK judge scorers stay DORMANT by design -- this eval is the
deterministic Monte-Carlo path, no LLM in the loop.

Determinism / stochastic stability
-----------------------------------
seed=42 and n=N (modest, 40-60) for every case. The gate keys on the MEAN over
all 10 (case x scorer) scores -- never a single noisy matchup -- which is the
load-bearing eval insight ("average-the-mean for stochastic stability").

Run it directly:
    python mtg-sim/tests/apl_quality.eval.py
Exit code mirrors apl_judge: 0 PASS / 1 FAIL / 2 ERROR. NOTE: a FAIL here means
the field-relative win-rate mean missed the bar -- it does NOT mean the harness
broke. The harness "ran clean" iff every case came back g1_source='bo3' with
error=None (the report checks and surfaces this).

CONVENTIONS: ASCII-only; '->' and '--' not unicode.
"""

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import eval_harness as eh  # noqa: E402


# --- eval configuration ----------------------------------------------------
N = 50          # modest Monte Carlo sample per matchup (task spec: 40-60)
SEED = 42       # fixed seed for reproducibility (task spec)
FORMAT = "modern"
THRESHOLD = 0.50  # "clears parity vs a strong field" -- principled, not tuned

# our APLs: (registry_key, label)
OUR_APLS = [
    ("temurprowess",   "Temur Prowess (field-gap)"),
    ("sultaimidrange", "Sultai Midrange (field-gap)"),
    ("grixismidrange", "Grixis Midrange (field-gap)"),
    ("borosenergy",    "Boros Energy (anchor)"),
    ("izzetprowess",   "Izzet Prowess (anchor)"),
]

# field opponents: (registry_key, short_id_for_case)
FIELD_OPPS = [
    ("amulettitan", "amulet"),
    ("yawgmoth",    "yawgmoth"),
]


def build_data() -> list:
    """5 our-APLs x 2 field opponents = 10 cases. case.id = '<apl>_vs_<opp>'."""
    cases = []
    for apl_key, _label in OUR_APLS:
        for opp_key, opp_short in FIELD_OPPS:
            cases.append(eh.EvalCase(
                id=f"{apl_key}_vs_{opp_short}",
                input={
                    "our_deck": apl_key,
                    "opp": opp_key,
                    "format": FORMAT,
                    "type": "fair",
                    "n": N,
                    "seed": SEED,
                },
                expected=None,  # no PT ground-truth wired; this is a relative bar
            ))
    return cases


def main() -> int:
    trace_path = os.path.join(
        _THIS_DIR, "..", "reports", "apl_quality_eval_2026-06-29.trace.jsonl")
    trace_path = os.path.normpath(trace_path)
    if os.path.exists(trace_path):
        os.remove(trace_path)

    # ONLY the Monte Carlo scorer is active. The judge scorers stay dormant.
    scorers = [eh.MonteCarloScorer()]
    print(f"  [gemma4/Anthropic judge scorers DORMANT by design -- "
          f"anthropic SDK available: {eh.anthropic_available()}]")
    print(f"  [running {len(OUR_APLS)}x{len(FIELD_OPPS)} = "
          f"{len(OUR_APLS)*len(FIELD_OPPS)} real Bo3 matchups at n={N} seed={SEED}]")

    report = eh.evalite(
        "apl-quality-winrate",
        data=build_data(),
        task=eh.MonteCarloScorer.run_matchup_task,   # the REAL sim task
        scorers=scorers,
        threshold=THRESHOLD,
        trace_path=trace_path,
    )

    print()
    print(report.summary())
    print(f"  trace -> {trace_path}")

    # --- per-APL aggregation (the runner only gives a global mean) ----------
    print()
    print("  per-APL mean winrate (avg over field opponents):")
    by_apl = {}
    bo3_count = 0
    total = 0
    for row in report.cases:
        cid = row["case_id"]
        apl = cid.rsplit("_vs_", 1)[0]
        sc = row["scores"].get("winrate_over_N", {})
        score = sc.get("score")
        meta = sc.get("metadata", {})
        total += 1
        if meta.get("g1_source") == "bo3":
            bo3_count += 1
        by_apl.setdefault(apl, []).append(score)
    for apl_key, _label in OUR_APLS:
        vals = [v for v in by_apl.get(apl_key, []) if v is not None]
        m = (sum(vals) / len(vals)) if vals else None
        m_s = "n/a" if m is None else f"{m:.3f}"
        print(f"    - {apl_key:16s}: {m_s}  (n_opps={len(vals)})")

    print()
    print(f"  harness health: {bo3_count}/{total} cases hit g1_source='bo3' "
          f"(real Bo3, not heuristic fallback)")
    print(f"  exit_code = {report.exit_code} "
          f"({'PASS' if report.passing else ('FAIL' if report.mean is not None else 'ERROR')})")
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
