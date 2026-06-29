"""
example_apl.eval.py -- a tiny evalite-shaped demo over eval_harness.py.

Run it directly:
    python mtg-sim/tests/example_apl.eval.py

It builds a 3-case data set, runs the MonteCarloScorer (winrate_over_N) over a
MOCKED task (run_matchup-style result dicts), gates mean >= threshold, and writes
a JSONL trace. The Monte Carlo scorer needs NO model, so the demo passes whether
or not Ollama / the Anthropic SDK are present -- it does NOT require a live model.

If gemma4 over Ollama happens to be reachable, the demo ALSO adds the gemma4
LLM-judge scorer (apl_judge via its llm= seam) as a reported-but-non-blocking
extra; it is skipped cleanly otherwise. The Anthropic judge is shown wired up but
stays gated behind the SDK (absent 2026-06-29).

Note: this file is named *.eval.py (not test_*.py) and has a dotted stem, so it is
NOT auto-collected by pytest -- it is the `python`-runnable demo. The hermetic
pytest assertions live in eval_harness.py (run `pytest .../eval_harness.py`).

CONVENTIONS: ASCII-only; '->' and '--' not unicode.
"""

import os
import sys

# eval_harness.py is a sibling in this same tests/ directory.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import eval_harness as eh  # noqa: E402


# --- data: 3 cases, each carrying a mocked run_matchup-style result dict ----
DATA = [
    eh.EvalCase(id="boros_vs_amulet",
                input={"sim_result": {"match": 80.0, "g1": 78.0, "n": 200,
                                      "seed": 42, "g1_source": "bo3"}},
                expected={"pt_truth_wr": 0.78}),
    eh.EvalCase(id="boros_vs_murktide",
                input={"sim_result": {"match": 70.0, "g1": 66.0, "n": 200,
                                      "seed": 43, "g1_source": "bo3"}},
                expected={"pt_truth_wr": 0.66}),
    eh.EvalCase(id="boros_vs_yawgmoth",
                input={"sim_result": {"match": 62.9, "g1": 60.0, "n": 200,
                                      "seed": 44, "g1_source": "bo3"}},
                expected={"pt_truth_wr": 0.629}),
]


def mocked_task(case: eh.EvalCase) -> dict:
    """The task: in a real eval this calls MonteCarloScorer.run_matchup_task(case)
    to run the sim. Here it just returns the pre-baked result so the demo needs no
    engine and no model."""
    return case.input["sim_result"]


def main() -> int:
    trace_path = os.path.join(
        os.environ.get("TEMP", _THIS_DIR), "example_apl_eval_trace.jsonl")
    if os.path.exists(trace_path):
        os.remove(trace_path)

    scorers = [eh.MonteCarloScorer()]

    # Optionally exercise the gemma4 judge ONLY if Ollama is reachable. Excluded
    # from the gate by returning None when unavailable, so this never blocks.
    try:
        import apl_judge
        if apl_judge.check_llm_available("gemma4"):
            print("  [gemma4 reachable -> adding non-blocking gemma4 judge scorer]")
            scorers.append(eh.Gemma4JudgeScorer())
        else:
            print("  [gemma4 not reachable -> MonteCarloScorer only]")
    except Exception as e:
        print(f"  [apl_judge import/probe skipped: {e}]")

    # The Anthropic judge stays gated behind the SDK (absent 2026-06-29).
    print(f"  [anthropic SDK available: {eh.anthropic_available()} "
          f"-> AnthropicJudgeScorer would skip cleanly if added]")

    report = eh.evalite(
        "example-apl-winrate",
        data=DATA, task=mocked_task, scorers=scorers,
        threshold=0.55, trace_path=trace_path,
    )

    print()
    print(report.summary())
    print(f"  trace -> {trace_path}")
    print(f"  exit_code = {report.exit_code} "
          f"({'PASS' if report.passing else 'FAIL/ERROR'})")
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
