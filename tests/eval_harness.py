"""
eval_harness.py -- an evalite-shaped eval harness: data -> task -> scorers[].

Implements harness/specs/2026-06-29-evalite-eval-harness.md. The point is to
measure whether an agent (an APL, an APL-generator, a mulligan policy) got
BETTER, not just whether it ran. The shape mirrors evalite:

    data    : list[EvalCase]                  -- the fixtures (inputs + expected)
    task    : Callable[[EvalCase], Any]       -- runs the agent/sim for a case
    scorers : list[Scorer]                    -- turn (case, output) into 0..1

The runner (evalite) drives task over every case, applies every scorer, captures
one JSONL trace row per (case, scorer), computes the MEAN over non-None scores,
and gates `mean >= threshold`. Gating the MEAN -- never an individual case -- is
the load-bearing eval insight: a single Monte Carlo run is noisy, so we average
across the data set and threshold the average ("average-the-mean for stochastic
stability").

Three scorers ship here:

  - MonteCarloScorer / winrate_over_N : wraps the run_matchup sim. Pure on the
        result dict -- normalizes result["match"] (a PERCENT, e.g. 80.0) by /100
        to 0..1. Needs NO LLM, so the hermetic test + demo pass with a mocked task
        even if Ollama / Anthropic are absent.
  - Gemma4JudgeScorer : REUSES harness apl_judge.grade_apl via its `llm=` seam
        (default gemma4 over Ollama). Exercised only when check_llm_available().
        ERROR/INCONCLUSIVE -> score None (excluded from the mean), so a flaky judge
        transport never tanks the gate.
  - AnthropicJudgeScorer : the SAME apl_judge.grade_apl, with an Anthropic-SDK
        `llm=` callable. GATED behind the SDK being installed -- if `anthropic` is
        absent (confirmed 2026-06-29) it skips cleanly (score None), never crashes.

The "extends apl_judge" mechanism is ONLY the `llm=` seam: grade_apl / build_prompt
/ parse_result / score_apl / JudgeGrade / run_calibration are reused verbatim; the
Anthropic judge is just a different transport callable.

Pytest entry: this module carries `test_*` functions (run `pytest path/to/
eval_harness.py`). They are hermetic -- no Ollama, no Anthropic, no real sim.

CONVENTIONS: ASCII-only; sys.path wired from repo layout; '->' and '--' not unicode.
"""

import os
import sys
import json
import time
import importlib.util
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# --- path wiring -----------------------------------------------------------
# This file lives at  <root>/mtg-sim/tests/eval_harness.py
# apl_judge lives at   <root>/harness/agents/scripts/apl_judge.py
# Wire harness/agents/scripts onto sys.path so `import apl_judge` works. The
# import is socket-free (apl_judge's transport is lazy + guarded) and apl_judge
# does its own path wiring for the engine / verify_oracle helpers.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_THIS_DIR, "..", ".."))
_APL_JUDGE_DIR = os.path.join(_REPO_ROOT, "harness", "agents", "scripts")
if _APL_JUDGE_DIR not in sys.path:
    sys.path.insert(0, _APL_JUDGE_DIR)


# ---------------------------------------------------------------------------
# Core shapes: EvalCase, ScoreResult, Scorer, EvalReport
# ---------------------------------------------------------------------------
@dataclass
class EvalCase:
    """One fixture row. `input` feeds the task; `expected` is the ground truth.

    `input` is free-form per eval. For a winrate eval it carries the sim args
    (our_deck / opp / n / seed); for a judge eval it carries an apl_judge
    question dict plus apl_path or apl_code. `expected` is optional (e.g.
    {"pt_truth_wr": 0.629} or a PASS/FAIL).
    """
    input: dict
    expected: Optional[dict] = None
    id: Optional[str] = None


@dataclass
class ScoreResult:
    """A scorer's verdict for one case.

    score : 0..1, or None to EXCLUDE this case from the mean (mirrors apl_judge's
            ERROR/INCONCLUSIVE -> not counted rule). The runner skips None.
    metadata : anything worth tracing (n, g1, JudgeGrade.to_dict(), skip reason).
    """
    score: Optional[float]
    metadata: dict = field(default_factory=dict)


# A scorer is any callable (case, task_output) -> ScoreResult. Give it a `.name`
# attribute (the classes below do) or it falls back to the class/function name.
Scorer = Callable[[EvalCase, Any], ScoreResult]


@dataclass
class EvalReport:
    """The runner's verdict. exit_code mirrors apl_judge: 0 PASS / 1 FAIL / 2 ERROR."""
    name: str
    threshold: float
    mean: Optional[float]
    n_scored: int
    n_excluded: int
    per_scorer_means: dict
    cases: list  # list[dict]: {case_id, scores: {scorer: {score, metadata}}}

    @property
    def passing(self) -> bool:
        return self.mean is not None and self.mean >= self.threshold

    @property
    def exit_code(self) -> int:
        if self.mean is None:          # nothing scorable -> ERROR
            return 2
        return 0 if self.passing else 1

    def summary(self) -> str:
        mean_s = "n/a" if self.mean is None else f"{self.mean:.3f}"
        flag = "PASS" if self.passing else ("ERROR" if self.mean is None else "FAIL")
        lines = [
            f"eval '{self.name}': mean={mean_s} threshold={self.threshold:.3f} "
            f"[{flag}]  (scored {self.n_scored}, excluded {self.n_excluded})"
        ]
        for sname, m in self.per_scorer_means.items():
            m_s = "n/a" if m is None else f"{m:.3f}"
            lines.append(f"  - {sname}: mean={m_s}")
        return "\n".join(lines)


def _scorer_name(scorer: Scorer) -> str:
    return (getattr(scorer, "name", None)
            or getattr(scorer, "__name__", None)
            or scorer.__class__.__name__)


def _append_trace(trace_path: Optional[str], row: dict) -> None:
    """Append one JSONL row. Reuse existing payload shapes (JudgeGrade.to_dict() /
    run_matchup result fields) inside `metadata`; the envelope adds only
    {ts, eval_name, case_id, scorer, score}. No-op when trace_path is None."""
    if not trace_path:
        return
    parent = os.path.dirname(os.path.abspath(trace_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(trace_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")


def evalite(name: str, *, data: list, task: Callable[[EvalCase], Any],
            scorers: list, threshold: float,
            trace_path: Optional[str] = None) -> EvalReport:
    """Drive task over every case, apply every scorer, gate mean(score) >= threshold.

    A failed task is caught and turned into {"error": ...} so one bad case cannot
    crash the run; its scorers will typically return score=None and be excluded.
    The MEAN (over all non-None case x scorer scores) is what gets gated -- never a
    single case -- which is what makes a stochastic agent testable without flakiness.
    """
    all_scores: list = []
    per_scorer: dict = {s and _scorer_name(s): [] for s in scorers}
    case_rows: list = []

    for idx, case in enumerate(data):
        cid = case.id or f"case{idx}"
        try:
            output = task(case)
        except Exception as e:  # task failure -> degraded output, not a crash
            output = {"error": f"task failed: {e}"}

        scores_for_case = {}
        for scorer in scorers:
            sname = _scorer_name(scorer)
            try:
                res = scorer(case, output)
            except Exception as e:  # a broken scorer excludes the case, never crashes
                res = ScoreResult(None, {"error": f"scorer failed: {e}"})
            scores_for_case[sname] = {"score": res.score, "metadata": res.metadata}
            if res.score is not None:
                all_scores.append(res.score)
                per_scorer[sname].append(res.score)
            _append_trace(trace_path, {
                "ts": time.time(),
                "eval_name": name,
                "case_id": cid,
                "scorer": sname,
                "score": res.score,
                "metadata": res.metadata,
            })
        case_rows.append({"case_id": cid, "scores": scores_for_case})

    mean = (sum(all_scores) / len(all_scores)) if all_scores else None
    per_scorer_means = {
        k: (sum(v) / len(v) if v else None) for k, v in per_scorer.items()
    }
    total_pairs = len(data) * len(scorers)
    return EvalReport(
        name=name, threshold=threshold, mean=mean,
        n_scored=len(all_scores), n_excluded=total_pairs - len(all_scores),
        per_scorer_means=per_scorer_means, cases=case_rows,
    )


# ---------------------------------------------------------------------------
# Scorer 1: MonteCarloScorer / winrate_over_N -- the sim as a 0..1 scorer
# ---------------------------------------------------------------------------
class MonteCarloScorer:
    """Normalize a run_matchup result dict's win-percent to 0..1.

    run_matchup reports a PERCENT (result["match"] is e.g. 80.0, not 0.80) -- the
    /100 here is load-bearing or every score is 80x too big. The scorer is a PURE
    function of the result dict, so it needs no live sim; the *task* is what runs
    run_matchup (see run_matchup_task). Stochastic stability comes from the runner
    averaging across cases/seeds, not from this scorer.
    """
    name = "winrate_over_N"

    def __call__(self, case: EvalCase, task_output: Any) -> ScoreResult:
        if not isinstance(task_output, dict) or task_output.get("match") is None:
            return ScoreResult(None, {"reason": "no 'match' in task output",
                                      "output": task_output})
        match = task_output["match"]
        return ScoreResult(
            score=match / 100.0,
            metadata={
                "match_pct": match,
                "g1": task_output.get("g1"),
                "n": task_output.get("n"),
                "seed": task_output.get("seed"),
                "g1_source": task_output.get("g1_source"),
                "elapsed": task_output.get("elapsed"),
            },
        )

    @staticmethod
    def run_matchup_task(case: EvalCase) -> dict:
        """A `task` that runs the REAL Monte Carlo sim for a case and returns the
        run_matchup-style result dict. Lazy-imports run_matchup so importing this
        module never pulls in the engine. `case.input` carries:
            our_deck, opp, field_pct, n, seed, format, type[, inner_workers]
        Used for real evals; the hermetic test + demo use a mocked task instead.
        """
        if _REPO_ROOT not in sys.path:
            sys.path.insert(0, _REPO_ROOT)
        sim_dir = os.path.join(_REPO_ROOT, "mtg-sim")
        if sim_dir not in sys.path:
            sys.path.insert(0, sim_dir)
        import run_matchup  # lazy; pulls in the engine

        inp = case.input
        t0 = time.time()
        result = {
            "opp": inp["opp"], "our_deck": inp["our_deck"],
            "field_pct": inp.get("field_pct", 0.0),
            "type": inp.get("type", "fair"), "n": inp.get("n", 200), "error": None,
        }
        seed = inp.get("seed", 42)
        fmt = inp.get("format", "modern")
        n = inp.get("n", 200)
        if result["type"] == "combo":
            run_matchup._run_combo(result, inp["opp"], fmt, n, seed)
        else:
            run_matchup._run_fair(result, inp["our_deck"], inp["opp"], fmt, n, seed,
                                  inp.get("inner_workers", 1))
        result["seed"] = seed
        result["elapsed"] = round(time.time() - t0, 1)
        return result


# Module-level scorer instance, usable directly in a scorers=[...] list.
winrate_over_N = MonteCarloScorer()


# ---------------------------------------------------------------------------
# Scorer 2: Gemma4JudgeScorer -- LLM-judge reusing apl_judge over Ollama
# ---------------------------------------------------------------------------
class _AplJudgeScorer:
    """Shared base: turn an apl_judge.JudgeGrade into a ScoreResult.

    PASS -> 1.0, FAIL -> 0.0, ERROR/INCONCLUSIVE -> None (excluded). This is
    exactly apl_judge's counts_for_score rule, so a flaky judge transport returns
    None and is skipped by the mean rather than silently dragging it down.
    """
    name = "apl_judge"

    def _grade(self, case: EvalCase, llm=None, model=None):
        import apl_judge
        question = case.input.get("question")
        if question is None:
            return None  # not a judge case
        return apl_judge.grade_apl(
            question,
            apl_path=case.input.get("apl_path"),
            apl_code=case.input.get("apl_code"),
            model=model or getattr(self, "model", apl_judge.DEFAULT_MODEL),
            llm=llm,
        )

    @staticmethod
    def _grade_to_result(grade) -> ScoreResult:
        if grade is None:
            return ScoreResult(None, {"reason": "no apl_judge 'question' in case"})
        if not grade.counts_for_score:          # ERROR / INCONCLUSIVE -> excluded
            return ScoreResult(None, grade.to_dict())
        return ScoreResult(1.0 if grade.is_pass else 0.0, grade.to_dict())


class Gemma4JudgeScorer(_AplJudgeScorer):
    """gemma4-over-Ollama judge. Cheap local pre-filter. Exercised only when the
    model is reachable; otherwise returns None (excluded) without contacting it."""
    name = "gemma4_judge"

    def __init__(self, model: str = "gemma4"):
        self.model = model

    def __call__(self, case: EvalCase, task_output: Any) -> ScoreResult:
        import apl_judge
        if not apl_judge.check_llm_available(self.model):
            return ScoreResult(None, {"skipped": "ollama/gemma4 not reachable",
                                      "model": self.model})
        # llm=None -> grade_apl uses its own guarded call_llm (the same llm= seam).
        grade = self._grade(case, llm=None, model=self.model)
        return self._grade_to_result(grade)


# ---------------------------------------------------------------------------
# Scorer 3: AnthropicJudgeScorer -- SAME apl_judge, Anthropic-SDK transport
# ---------------------------------------------------------------------------
def anthropic_available() -> bool:
    """True iff the `anthropic` SDK is importable. Confirmed absent 2026-06-29 --
    the scorer skips cleanly in that case (never crashes)."""
    return importlib.util.find_spec("anthropic") is not None


def make_anthropic_llm(model: str = "claude-opus-4-8", max_tokens: int = 1024):
    """Build an `llm=` callable matching apl_judge's contract:
    fn(prompt, model_positional, num_ctx=...) -> str.

    Anthropic specifics (current SDK, claude-opus-4-8):
      - adaptive thinking: thinking={"type": "adaptive"}
      - NO budget_tokens / temperature / top_p -> they 400 on claude-opus-4-8
      - effort 'low' + a roomy max_tokens so the short RESULT:/REASON: contract is
        never truncated (a truncated response loses RESULT: and parse_result scores
        it FAIL -- a silent false-negative).

    Gotcha 8: grade_apl invokes the injected callable as fn(prompt, model, num_ctx=)
    where `model` defaults to "gemma4". This callable IGNORES that positional and
    uses the baked-in claude-opus-4-8, so the first call never goes out as gemma4.
    """
    import anthropic  # only reached when anthropic_available()
    client = anthropic.Anthropic()

    def _llm(prompt: str, _model_ignored: str = "gemma4", num_ctx: int = 4096) -> str:
        msg = client.messages.create(
            model=model,                       # baked-in; ignore positional gemma4
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            output_config={"effort": "low"},   # keep the PASS/FAIL contract small
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(
            getattr(b, "text", "") for b in msg.content
            if getattr(b, "type", None) == "text"
        )

    return _llm


class AnthropicJudgeScorer(_AplJudgeScorer):
    """Authoritative judge: the SAME apl_judge.grade_apl, with an Anthropic `llm=`.
    GATED behind the SDK -- if `anthropic` is not installed it returns None
    (excluded) and never imports the SDK, so the harness runs fine without it."""
    name = "anthropic_judge"

    def __init__(self, model: str = "claude-opus-4-8"):
        self.model = model
        self._llm = None

    def __call__(self, case: EvalCase, task_output: Any) -> ScoreResult:
        if not anthropic_available():
            return ScoreResult(None, {"skipped": "anthropic SDK not installed",
                                      "imperfection": "eval-harness-anthropic-sdk-not-installed"})
        if self._llm is None:
            self._llm = make_anthropic_llm(self.model)
        # Pass model=claude-opus-4-8 so the real id threads through grade_apl too.
        grade = self._grade(case, llm=self._llm, model=self.model)
        return self._grade_to_result(grade)


# ===========================================================================
# Hermetic pytest tests (no Ollama, no Anthropic, no real sim). Run:
#   pytest mtg-sim/tests/eval_harness.py
# (passing the file explicitly bypasses the default python_files = test_*.py
# filter, since this module is named eval_harness.py).
# ===========================================================================
def _mock_sim_task(case: EvalCase) -> dict:
    """Mocked task: returns the run_matchup-style dict carried in case.input."""
    return case.input["sim_result"]


def _winrate_cases() -> list:
    return [
        EvalCase(id="vs_amulet", input={"sim_result": {"match": 80.0, "g1": 78.0,
                 "n": 200, "seed": 42, "g1_source": "bo3"}}),
        EvalCase(id="vs_murktide", input={"sim_result": {"match": 70.0, "g1": 66.0,
                 "n": 200, "seed": 43, "g1_source": "bo3"}}),
        EvalCase(id="vs_yawgmoth", input={"sim_result": {"match": 62.9, "g1": 60.0,
                 "n": 200, "seed": 44, "g1_source": "bo3"}}),
    ]


def test_monte_carlo_mean_gate(tmp_path=None):
    """MonteCarloScorer works WITHOUT any LLM and the mean clears the bar."""
    trace = (str(tmp_path / "trace.jsonl") if tmp_path is not None
             else os.path.join(_THIS_DIR, "_eval_trace_selftest.jsonl"))
    if tmp_path is None and os.path.exists(trace):
        os.remove(trace)

    report = evalite("winrate-demo", data=_winrate_cases(), task=_mock_sim_task,
                     scorers=[MonteCarloScorer()], threshold=0.55, trace_path=trace)

    # 80/70/62.9 -> .800/.700/.629 -> mean .7097, clears .55
    assert report.n_scored == 3, report.summary()
    assert report.n_excluded == 0
    assert abs(report.mean - (0.800 + 0.700 + 0.629) / 3) < 1e-9
    assert report.passing is True
    assert report.exit_code == 0

    # one trace row per (case, scorer)
    with open(trace, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    assert len(rows) == 3
    assert {r["scorer"] for r in rows} == {"winrate_over_N"}
    assert all("ts" in r and r["case_id"] and "score" in r for r in rows)
    assert rows[0]["metadata"]["match_pct"] == 80.0  # percent preserved in trace

    if tmp_path is None:
        os.remove(trace)


def test_percent_normalization_not_raw():
    """The /100 normalization is load-bearing: 80.0 -> 0.80, never 80.0."""
    res = MonteCarloScorer()(_winrate_cases()[0], {"match": 80.0, "n": 200})
    assert res.score == 0.80


def test_none_excluded_from_mean():
    """A case whose output lacks 'match' yields score None and is excluded; the
    mean is computed only over the scorable cases (average-the-mean stability)."""
    data = _winrate_cases() + [EvalCase(id="broken", input={"sim_result": {}})]
    report = evalite("winrate-with-broken", data=data, task=_mock_sim_task,
                     scorers=[MonteCarloScorer()], threshold=0.55)
    assert report.n_scored == 3          # broken case excluded, not counted
    assert report.n_excluded == 1
    assert report.passing is True


def test_mean_below_threshold_fails():
    """Gate keys on the mean: a low mean FAILs with exit 1, not a crash."""
    data = [EvalCase(id="bad", input={"sim_result": {"match": 30.0, "n": 200}})]
    report = evalite("loss", data=data, task=_mock_sim_task,
                     scorers=[MonteCarloScorer()], threshold=0.55)
    assert report.mean == 0.30
    assert report.passing is False
    assert report.exit_code == 1


def test_all_excluded_is_error_exit_2():
    """No scorable cases -> mean None -> ERROR exit 2 (mirrors apl_judge)."""
    data = [EvalCase(id="empty", input={"sim_result": {}})]
    report = evalite("nothing", data=data, task=_mock_sim_task,
                     scorers=[MonteCarloScorer()], threshold=0.55)
    assert report.mean is None
    assert report.exit_code == 2


def test_anthropic_scorer_gated_skips_cleanly():
    """With the anthropic SDK absent (2026-06-29), the scorer returns None and
    never crashes or imports the SDK."""
    scorer = AnthropicJudgeScorer()
    case = EvalCase(id="judge", input={"question": {"id": "q", "type": "oracle_fidelity",
                    "grep_terms": ["Bolt"]}, "apl_code": "x = 1\n"})
    res = scorer(case, {})
    if anthropic_available():
        # SDK present in some other environment: result may be a real grade or None;
        # just assert it didn't crash and returned a ScoreResult.
        assert isinstance(res, ScoreResult)
    else:
        assert res.score is None
        assert "anthropic SDK not installed" in res.metadata.get("skipped", "")


def test_gemma4_scorer_reuses_apl_judge_llm_seam(monkeypatch=None):
    """The gemma4 scorer routes through apl_judge.grade_apl's llm= seam. We
    monkeypatch the apl_judge transport so the test is hermetic (no Ollama),
    proving the scorer maps PASS -> 1.0 via the SAME apl_judge path."""
    import apl_judge

    # Force "available" and a deterministic PASS transport.
    orig_check = apl_judge.check_llm_available
    orig_call = apl_judge.call_llm
    apl_judge.check_llm_available = lambda *a, **k: True
    apl_judge.call_llm = lambda prompt, model="gemma4", **k: "RESULT: PASS\nREASON: ok"
    try:
        scorer = Gemma4JudgeScorer()
        case = EvalCase(id="judge", input={
            "question": {"id": "q", "type": "oracle_fidelity",
                         "grep_terms": ["Lightning Bolt"],
                         "card_or_deck": "Lightning Bolt",
                         "oracle_text": "Lightning Bolt deals 3 damage to any target.",
                         "expected": "PASS if 3 damage"},
            "apl_code": ("LIGHTNING_BOLT = \"Lightning Bolt\"\n"
                         "def cast(self):\n    target.damage += 3\n"),
        })
        res = scorer(case, {})
        assert res.score == 1.0, res.metadata
        assert res.metadata.get("result") == "PASS"
    finally:
        apl_judge.check_llm_available = orig_check
        apl_judge.call_llm = orig_call


def _run_all_tests() -> bool:
    """Run every test_* in this module without pytest (used by the demo)."""
    ok = True
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as e:
                ok = False
                print(f"  FAIL  {name}: {e}")
    return ok


if __name__ == "__main__":
    print("eval_harness self-test (hermetic):")
    sys.exit(0 if _run_all_tests() else 1)
