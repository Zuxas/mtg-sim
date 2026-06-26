#!/usr/bin/env python3
"""arl_distill.py -- RESCOPED distillation pass for one deck slug.

IMPORTANT SCOPE NOTE
--------------------
The full sequencing-heuristic distillation described in the ARL spec
(card_timing / decision_point / mana_hold events streamed to
logs/sequencing/<slug>_<date>.jsonl) does NOT exist: the engine emits no
such JSONL and ARL is forbidden from touching engine/ to add the
instrumentation (that is P0 human work, out of ARL scope).

So this tool is rescoped to consume the structured artifacts that DO exist:
  - data/matchup_jobs/<slug>/*.json   (per-matchup gauntlet results)
  - the matching results entry in loop_state.json (via arl_state)

It emits a human-readable markdown summary to docs/distill/<slug>.md:
  - overall field-weighted match win rate (FWR)
  - best 5 / worst 5 matchups by match win%
  - simple favored / even / unfavored rollups
  - candidate mutation targets = worst 3 matchups with a one-line note

CLI:
    python arl_distill.py <deck_slug> [--min-delta 3.0]

--min-delta sets the half-width (in percentage points) of the "even" band
around 50% used for the favored/unfavored rollups.

ASCII-only output. Exit 0 on success (including "no data" case), 1 on error.
"""

import sys
import os
import json
import glob
import argparse

# --- Cross-repo sys.path setup -------------------------------------------------
SIM_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_SCRIPTS = os.path.abspath(
    os.path.join(SIM_ROOT, "..", "harness", "agents", "scripts")
)
for _p in (SIM_ROOT, HARNESS_SCRIPTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

MATCHUP_JOBS_DIR = os.path.join(SIM_ROOT, "data", "matchup_jobs")
DISTILL_DIR = os.path.join(SIM_ROOT, "docs", "distill")

SCOPE_NOTE = (
    "NOTE: Full sequencing-heuristic distillation "
    "(card_timing/decision_point/mana_hold) requires engine instrumentation "
    "under engine/, which is P0 human work and out of ARL scope. This summary "
    "is derived from gauntlet matchup JSON only."
)


# --- Optional helpers (lazy/guarded) ------------------------------------------
def _load_arl_state():
    """Load loop_state via arl_state. Returns {} on any failure."""
    try:
        import arl_state  # type: ignore
        return arl_state.load_state()
    except Exception:
        return {}


def _find_result_entry(state, slug):
    """Return the results entry whose id matches slug, or None."""
    if not isinstance(state, dict):
        return None
    for r in state.get("results", []) or []:
        if isinstance(r, dict) and r.get("id") == slug:
            return r
    return None


# --- Engine-fidelity gate (archetype-capability-profiles spec, 2026-06-26) -----
# Only results with confidence in {high, medium} are trustworthy enough to
# distill heuristics from. low/unmodelable results are skipped (skip-noted) so
# the loop never turns engine-gap-tainted gauntlet numbers into APL candidates
# or playbook lines. A result with no confidence field defaults to "high" (the
# arl_state schema default), so legacy/un-gated results still distill.
DISTILLABLE_CONFIDENCE = ("high", "medium")
_QUALITY_VOCAB = ("high", "medium", "low", "unmodelable")


def _confidence_of(result_entry):
    """Normalized confidence of a result entry. Defaults to 'high'.

    Unknown / out-of-vocab values coerce to 'low' so a typo fails safe (gets
    skipped) rather than reading as trustworthy.
    """
    if not isinstance(result_entry, dict):
        return "high"
    raw = result_entry.get("confidence")
    if raw is None or raw == "":
        return "high"
    if isinstance(raw, str):
        v = raw.strip().lower()
        if v in _QUALITY_VOCAB:
            return v
    return "low"


def render_skip_md(slug, result_entry, confidence):
    """Short skip-note markdown recording why distillation was withheld."""
    bi = []
    if isinstance(result_entry, dict):
        bi = result_entry.get("blocking_imperfections") or []
    lines = []
    lines.append("# ARL distillation summary: %s" % slug)
    lines.append("")
    lines.append("> %s" % SCOPE_NOTE)
    lines.append("")
    lines.append("## SKIPPED -- low-confidence result (engine-fidelity gate)")
    lines.append("")
    lines.append("- confidence: %s" % confidence)
    if isinstance(result_entry, dict):
        if result_entry.get("data_quality"):
            lines.append("- data_quality: %s" % result_entry.get("data_quality"))
        if result_entry.get("verdict"):
            lines.append("- verdict: %s" % result_entry.get("verdict"))
    if bi:
        lines.append("- blocking_imperfections:")
        for imp in bi:
            lines.append("  - %s" % imp)
    lines.append("")
    lines.append("No heuristics were distilled from this result. Distillation "
                 "only runs for confidence in {high, medium} so "
                 "engine-gap-tainted gauntlet numbers never become APL "
                 "candidates or playbook lines. Once the blocking mechanic is "
                 "modeled and the result re-runs at high/medium confidence, "
                 "distillation will proceed normally.")
    lines.append("")
    return "\n".join(lines) + "\n"


# --- Matchup JSON loading ------------------------------------------------------
def load_matchups(slug):
    """Load all matchup JSON records for a slug.

    Returns (valid, skipped):
      valid   = list of dicts with usable 'match' win% (error is None)
      skipped = list of (filename, reason) tuples
    """
    deck_dir = os.path.join(MATCHUP_JOBS_DIR, slug)
    valid = []
    skipped = []
    if not os.path.isdir(deck_dir):
        return None, None  # signals "no dir at all"

    for path in sorted(glob.glob(os.path.join(deck_dir, "*.json"))):
        fname = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                rec = json.load(f)
        except (OSError, ValueError) as exc:
            skipped.append((fname, "unreadable: %s" % exc))
            continue
        if not isinstance(rec, dict):
            skipped.append((fname, "not a JSON object"))
            continue
        if rec.get("error"):
            skipped.append((fname, "error=%s" % rec.get("error")))
            continue
        match = rec.get("match")
        if match is None:
            skipped.append((fname, "no 'match' field"))
            continue
        try:
            rec["_match"] = float(match)
        except (TypeError, ValueError):
            skipped.append((fname, "non-numeric match=%r" % match))
            continue
        # field_pct is optional; default to 0.0 (unweighted contribution).
        try:
            rec["_field_pct"] = float(rec.get("field_pct") or 0.0)
        except (TypeError, ValueError):
            rec["_field_pct"] = 0.0
        rec["_opp"] = rec.get("opp") or os.path.splitext(fname)[0]
        valid.append(rec)
    return valid, skipped


# --- Analysis ------------------------------------------------------------------
def compute_fwr(valid):
    """Field-weighted match win rate.

    If total field weight is 0 (no field_pct anywhere), fall back to a simple
    unweighted mean. Returns (fwr, method) or (None, None) if no data.
    """
    if not valid:
        return None, None
    total_w = sum(r["_field_pct"] for r in valid)
    if total_w > 0:
        fwr = sum(r["_match"] * r["_field_pct"] for r in valid) / total_w
        return fwr, "field-weighted"
    fwr = sum(r["_match"] for r in valid) / len(valid)
    return fwr, "unweighted mean (no field_pct present)"


def rollups(valid, min_delta):
    """Bucket matchups into favored / even / unfavored around 50%.

    'even' band = match win% within +/- min_delta of 50.
    Returns dict with counts and average match% per bucket.
    """
    fav, even, unfav = [], [], []
    for r in valid:
        m = r["_match"]
        if m > 50.0 + min_delta:
            fav.append(r)
        elif m < 50.0 - min_delta:
            unfav.append(r)
        else:
            even.append(r)

    def _avg(rs):
        return (sum(x["_match"] for x in rs) / len(rs)) if rs else None

    return {
        "favored": (len(fav), _avg(fav)),
        "even": (len(even), _avg(even)),
        "unfavored": (len(unfav), _avg(unfav)),
    }


def _meta_swap_hint(our_deck, opp_name, fmt):
    """Best-effort tournament-data note via meta_bridge. Returns str or ''.

    Guarded: meta_bridge / DB may be absent. Never raises.
    """
    if not our_deck or not fmt:
        return ""
    try:
        import meta_bridge  # type: ignore
        real = meta_bridge.get_real_matchup(our_deck, opp_name, fmt)
        if real is not None:
            return " (tournament G1 ~%.1f%% per meta_bridge)" % real
    except Exception:
        return ""
    return ""


# --- Markdown rendering --------------------------------------------------------
def _fmt_pct(v):
    return "%.1f%%" % v if isinstance(v, (int, float)) else "n/a"


def render_md(slug, valid, skipped, fwr, fwr_method, buckets,
              result_entry, min_delta):
    lines = []
    lines.append("# ARL distillation summary: %s" % slug)
    lines.append("")
    lines.append("> %s" % SCOPE_NOTE)
    lines.append("")

    # Overall
    lines.append("## Overall")
    lines.append("")
    lines.append("- Matchups analyzed: %d" % len(valid))
    lines.append("- Overall FWR (%s): %s" % (fwr_method, _fmt_pct(fwr)))
    if result_entry:
        lines.append("- loop_state result entry found (id=%s):" % slug)
        if result_entry.get("fwr") is not None:
            lines.append("  - recorded fwr: %s" % _fmt_pct(result_entry.get("fwr")))
        if result_entry.get("verdict"):
            lines.append("  - verdict: %s" % result_entry.get("verdict"))
        if result_entry.get("hypothesis"):
            lines.append("  - hypothesis: %s" % result_entry.get("hypothesis"))
    else:
        lines.append("- loop_state result entry: none (no matching id in "
                     "loop_state.json results)")
    lines.append("")

    # Rollups
    lines.append("## Rollups (even band = +/- %.1fpp around 50%%)" % min_delta)
    lines.append("")
    for label in ("favored", "even", "unfavored"):
        n, avg = buckets[label]
        lines.append("- %-9s: %2d matchups, avg match win%% %s"
                     % (label, n, _fmt_pct(avg)))
    lines.append("")

    # Best / worst
    ordered = sorted(valid, key=lambda r: r["_match"], reverse=True)
    best = ordered[:5]
    worst = list(reversed(ordered[-5:])) if len(ordered) >= 1 else []

    lines.append("## Best 5 matchups (by match win%)")
    lines.append("")
    lines.append("| Opponent | Match% | G1 | G2 | G3 | Field% | src |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in best:
        lines.append("| %s | %.1f | %s | %s | %s | %.1f | %s |" % (
            r["_opp"], r["_match"],
            _g(r, "g1"), _g(r, "g2"), _g(r, "g3"),
            r["_field_pct"], r.get("g1_source", "?")))
    lines.append("")

    lines.append("## Worst 5 matchups (by match win%)")
    lines.append("")
    lines.append("| Opponent | Match% | G1 | G2 | G3 | Field% | src |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in worst:
        lines.append("| %s | %.1f | %s | %s | %s | %.1f | %s |" % (
            r["_opp"], r["_match"],
            _g(r, "g1"), _g(r, "g2"), _g(r, "g3"),
            r["_field_pct"], r.get("g1_source", "?")))
    lines.append("")

    # Candidate mutation targets = worst 3
    our_deck = valid[0].get("our_deck") if valid else None
    fmt = None
    if result_entry:
        fmt = result_entry.get("format") or result_entry.get("target_format")
    targets = list(reversed(ordered[-3:]))
    lines.append("## Candidate mutation targets (worst 3 matchups)")
    lines.append("")
    if not targets:
        lines.append("- none")
    for r in targets:
        hint = _meta_swap_hint(our_deck, r["_opp"], fmt)
        lines.append("- vs %s: match win%% %.1f (field %.1f%%, type=%s)%s "
                     "-- weakest result; candidate for sideboard/list tuning."
                     % (r["_opp"], r["_match"], r["_field_pct"],
                        r.get("type", "?"), hint))
    lines.append("")

    # Skipped
    if skipped:
        lines.append("## Skipped matchup files")
        lines.append("")
        for fname, reason in skipped:
            lines.append("- %s: %s" % (fname, reason))
        lines.append("")

    return "\n".join(lines) + "\n"


def _g(rec, key):
    v = rec.get(key)
    return ("%.1f" % v) if isinstance(v, (int, float)) else "-"


# --- Main ----------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="RESCOPED ARL distillation: summarize gauntlet matchup "
                    "JSON for one deck slug into docs/distill/<slug>.md.")
    parser.add_argument("deck_slug", help="deck slug (matchup_jobs subdir)")
    parser.add_argument("--min-delta", type=float, default=3.0,
                        help="half-width (pp) of the 'even' band around 50%% "
                             "for rollups (default 3.0)")
    args = parser.parse_args(argv)

    slug = args.deck_slug
    min_delta = args.min_delta

    print(SCOPE_NOTE)
    print("")

    valid, skipped = load_matchups(slug)

    if valid is None:
        # No matchup_jobs directory for this slug -> not an error.
        print("No matchup_jobs found for slug '%s' (looked in %s)."
              % (slug, os.path.join(MATCHUP_JOBS_DIR, slug)))
        print("Nothing to distill. Exiting 0.")
        return 0

    if not valid:
        print("Found matchup_jobs dir for '%s' but no usable matchup records."
              % slug)
        if skipped:
            print("Skipped %d file(s):" % len(skipped))
            for fname, reason in skipped:
                print("  - %s: %s" % (fname, reason))
        print("Nothing to distill. Exiting 0.")
        return 0

    state = _load_arl_state()
    result_entry = _find_result_entry(state, slug)

    # Engine-fidelity gate: never distill heuristics from low/unmodelable
    # results. Skip-note instead so the gap is visible, not silent.
    confidence = _confidence_of(result_entry)
    if confidence not in DISTILLABLE_CONFIDENCE:
        print("SKIP: result confidence=%s (not in {high, medium})." % confidence)
        print("Engine-fidelity gate: refusing to distill heuristics from a "
              "low/unmodelable result.")
        bi = (result_entry or {}).get("blocking_imperfections") or []
        if bi:
            print("Blocking imperfections:")
            for imp in bi:
                print("  - %s" % imp)
        try:
            os.makedirs(DISTILL_DIR, exist_ok=True)
            out_path = os.path.join(DISTILL_DIR, "%s.md" % slug)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(render_skip_md(slug, result_entry, confidence))
            print("")
            print("Wrote skip-note: %s" % out_path)
        except OSError as exc:
            print("ERROR writing skip-note markdown: %s" % exc)
            return 1
        return 0

    fwr, fwr_method = compute_fwr(valid)
    buckets = rollups(valid, min_delta)

    # Console summary (ASCII).
    print("Deck slug: %s" % slug)
    print("Matchups analyzed: %d" % len(valid))
    print("Overall FWR (%s): %s" % (fwr_method, _fmt_pct(fwr)))
    print("Rollups (even band +/- %.1fpp):" % min_delta)
    for label in ("favored", "even", "unfavored"):
        n, avg = buckets[label]
        print("  %-9s: %2d  avg %s" % (label, n, _fmt_pct(avg)))

    ordered = sorted(valid, key=lambda r: r["_match"], reverse=True)
    print("Worst 3 (candidate mutation targets):")
    for r in reversed(ordered[-3:]):
        print("  vs %-28s match %.1f%%  field %.1f%%"
              % (r["_opp"], r["_match"], r["_field_pct"]))

    md = render_md(slug, valid, skipped, fwr, fwr_method, buckets,
                   result_entry, min_delta)

    try:
        os.makedirs(DISTILL_DIR, exist_ok=True)
        out_path = os.path.join(DISTILL_DIR, "%s.md" % slug)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)
    except OSError as exc:
        print("ERROR writing markdown: %s" % exc)
        return 1

    print("")
    print("Wrote: %s" % out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
