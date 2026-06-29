# APL Quality Eval -- 2026-06-29

End-to-end validation of the evalite-shaped eval harness
(`mtg-sim/tests/eval_harness.py`) on **real** Monte Carlo sims. This is the
first time the harness has been driven over actual decks rather than pre-baked
result dicts (cf. `tests/example_apl.eval.py`, which mocks the task).

- **Eval script:** `mtg-sim/tests/apl_quality.eval.py`
- **Harness:** `mtg-sim/tests/eval_harness.py` (unchanged by this lane)
- **Trace (JSONL):** `mtg-sim/reports/apl_quality_eval_2026-06-29.trace.jsonl`
- **Scorer:** `MonteCarloScorer` (`winrate_over_N`) only -- pure function of the
  `run_matchup` result dict, **no live model**.
- **Sim path:** `MonteCarloScorer.run_matchup_task` -> `run_matchup._run_fair`
  (`type='fair'`) -> real two-player match-APL Bo3. All cases confirmed
  `g1_source='bo3'` (not the heuristic fallback).
- **Sample / seed:** `n=50`, `seed=42` per matchup (modest Monte Carlo).
- **Gate:** mean of all 10 (case x scorer) scores `>= 0.50`.

## What was scored

Five "our" APLs, each vs the same two Modern field opponents (5 x 2 = 10 cases).
Each opponent resolves to a real `MATCH_APL` + deck file, which is what forces
the real-Bo3 (Path A) route on both sides.

| Our APL | Role | Deck file |
|---|---|---|
| `temurprowess`   | field-gap (new 2026-06-28, "WF-1, confidence medium") | `decks/temur_prowess_standard.txt` |
| `sultaimidrange` | field-gap (new 2026-06-28)                            | `decks/sultai_midrange_modern.txt` |
| `grixismidrange` | field-gap (new 2026-06-28)                            | `decks/dimir_murktide_modern.txt` |
| `borosenergy`    | canonical anchor                                      | `decks/boros_energy_modern.txt` |
| `izzetprowess`   | canonical anchor                                      | `decks/izzet_prowess_modern.txt` |

Field opponents: `amulettitan`, `yawgmoth`.

## Per-matchup scores (n=50, seed=42)

| Case | Match WR % | G1 % | Score (0-1) | g1_source |
|---|---|---|---|---|
| temurprowess_vs_amulet     | 68.0  | 68.0  | 0.680 | bo3 |
| temurprowess_vs_yawgmoth   | 100.0 | 98.0  | 1.000 | bo3 |
| sultaimidrange_vs_amulet   | 96.0  | 82.0  | 0.960 | bo3 |
| sultaimidrange_vs_yawgmoth | 96.0  | 88.0  | 0.960 | bo3 |
| grixismidrange_vs_amulet   | 92.0  | 78.0  | 0.920 | bo3 |
| grixismidrange_vs_yawgmoth | 96.0  | 90.0  | 0.960 | bo3 |
| borosenergy_vs_amulet      | 98.0  | 94.0  | 0.980 | bo3 |
| borosenergy_vs_yawgmoth    | 98.0  | 100.0 | 0.980 | bo3 |
| izzetprowess_vs_amulet     | 100.0 | 98.0  | 1.000 | bo3 |
| izzetprowess_vs_yawgmoth   | 100.0 | 96.0  | 1.000 | bo3 |

## Per-APL means (avg over the two field opponents)

| Our APL | Mean score |
|---|---|
| temurprowess   | 0.840 |
| sultaimidrange | 0.960 |
| grixismidrange | 0.940 |
| borosenergy    | 0.980 |
| izzetprowess   | 1.000 |

## Verdict

- **Global mean: 0.944** over 10 scored cases (0 excluded).
- **Threshold: 0.500.**
- **Eval gate: PASS** (exit_code 0). `0.944 >= 0.500`.
- **Harness health: 10/10 cases hit `g1_source='bo3'`** with `error=None` -- every
  matchup ran the real two-player Bo3 engine, none silently fell back to the
  Path B heuristic. This is the load-bearing validation result: **the eval
  harness runs end-to-end on real sims.**

## Honest notes / caveats

- **This is the deterministic Monte-Carlo scorer.** The `Gemma4JudgeScorer`
  (Ollama) and `AnthropicJudgeScorer` (Anthropic SDK) stayed **dormant by
  design** -- no live model was contacted (anthropic SDK confirmed absent;
  gemma4 not probed). The harness's LLM-judge seam is wired and unit-tested
  hermetically in `eval_harness.py`, but it is not exercised here.

- **Win rates skew very high (mean 0.944), so the 0.50 bar is cleared trivially.**
  This validates the *plumbing*, not a claim that these decks beat the real
  Modern field ~94% of the time. The most likely cause is that the **opponent**
  match-APLs (`AmuletTitanMatchAPL`, `YawgmothMatchAPL`) under-pilot their decks
  in the two-player engine relative to how the "our" side is driven -- a known
  general limitation of asymmetric APL maturity, not a scorer bug. Note also
  that neither `amulet` nor `yawgmoth` is in `run_matchup`'s `INTERACTIVE`
  credibility-cap set, so no >75% cap fired to compress these numbers.

- **`temurprowess` is the one interesting spread:** 68% vs amulet but 100% vs
  yawgmoth. It is also the lowest per-APL mean (0.840) and is flagged
  "confidence medium" in the repo notes -- a reasonable first candidate if/when
  someone wants to dig into APL quality rather than harness plumbing.

- **Threshold was chosen on principle (0.50 = parity vs a strong field), not
  tuned to force a PASS.** A FAIL here would have meant the field-relative mean
  missed the bar -- it would *not* have meant the harness broke. Harness
  correctness is judged by the `g1_source='bo3'` / `error=None` health check
  above, which is independent of the win-rate gate.

- **Reproduce:** `python mtg-sim/tests/apl_quality.eval.py` (deterministic at
  `seed=42`, `n=50`; no model required).
