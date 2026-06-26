#!/usr/bin/env python3
"""arl_status.py -- READ-ONLY status dump for the Autonomous Research Loop.

Zero side effects: this script never writes loop_state.json (or anything else).
It loads the loop state via arl_state.load_state() and prints an ASCII-only
human summary:

    - header line (status / mode / hypothesis / iteration / target_format /
      promote_threshold)
    - top-5 promoted decks by FWR with their vs_field summary
    - next 3 pending queue items with their hitl flag
    - active blockers with any suggested resolution
    - the most recent applied steer (if a steer history is present)

If the loop is paused for human-in-the-loop review, it prints the candidate id
and the exact resume command.

Usage:
    python arl_status.py

Always exits 0. Never writes state.
"""

import os
import sys

# --- Cross-repo sys.path setup -------------------------------------------------
SIM_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_SCRIPTS = os.path.abspath(
    os.path.join(SIM_ROOT, "..", "harness", "agents", "scripts")
)
for _p in (SIM_ROOT, HARNESS_SCRIPTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# --- Small formatting helpers --------------------------------------------------
def _fmt_pct(val):
    """Format a numeric percentage, tolerating None / non-numeric input."""
    if val is None:
        return "?"
    try:
        return "%.1f%%" % float(val)
    except (TypeError, ValueError):
        return str(val)


def _first_present(d, keys, default=None):
    """Return d[k] for the first key k in `keys` that exists and is not None."""
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _vs_field_summary(vs_field, max_items=6):
    """Render a vs_field dict ({opp: winrate}) as a compact, sorted string."""
    if not isinstance(vs_field, dict) or not vs_field:
        return "(no matchup data)"
    pairs = []
    for opp, wr in vs_field.items():
        try:
            key = float(wr)
        except (TypeError, ValueError):
            key = -1.0
        pairs.append((key, opp, wr))
    pairs.sort(key=lambda t: -t[0])
    shown = pairs[:max_items]
    parts = ["%s %s" % (opp, _fmt_pct(wr)) for _, opp, wr in shown]
    extra = len(pairs) - len(shown)
    if extra > 0:
        parts.append("(+%d more)" % extra)
    return ", ".join(parts)


def _result_fwr(result):
    """Pull a numeric FWR out of a result record, or None."""
    if not isinstance(result, dict):
        return None
    val = result.get("fwr")
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# --- Section printers ----------------------------------------------------------
def _print_header(state):
    print("=" * 64)
    print("  ARL STATUS")
    print("=" * 64)
    print("  status:           %s" % state.get("status", "?"))
    print("  mode:             %s" % state.get("mode", "?"))
    print("  target_format:    %s" % state.get("target_format", "?"))
    print("  iteration:        %s" % state.get("iteration", "?"))
    print("  promote_threshold:%s" % (" %s" % _fmt_pct(state.get("promote_threshold"))))
    hyp = state.get("hypothesis")
    if not hyp:
        hyp = "(none set)"
    print("  hypothesis:       %s" % hyp)
    last = state.get("last_updated")
    if last:
        print("  last_updated:     %s" % last)


def _print_promoted(state):
    print("")
    print("-" * 64)
    print("  TOP PROMOTED (by FWR, max 5)")
    print("-" * 64)
    promoted = state.get("promoted") or []
    results = state.get("results") or []

    # Index results by id so we can pull FWR + vs_field for each promoted slug.
    by_id = {}
    for r in results:
        if isinstance(r, dict) and r.get("id") is not None:
            # Keep the latest result for a given id (results append over time).
            by_id[r["id"]] = r

    if not promoted:
        print("  (none promoted yet)")
        return

    enriched = []
    for slug in promoted:
        res = by_id.get(slug)
        enriched.append((slug, res, _result_fwr(res)))

    # Sort by FWR descending; unknown FWR (None) sinks to the bottom.
    enriched.sort(key=lambda t: (t[2] is None, -(t[2] if t[2] is not None else 0.0)))

    for i, (slug, res, fwr) in enumerate(enriched[:5], start=1):
        print("  %d. %-32s FWR %s" % (i, slug, _fmt_pct(fwr)))
        vs_field = res.get("vs_field") if isinstance(res, dict) else None
        print("       vs field: %s" % _vs_field_summary(vs_field))


def _print_queue(state):
    print("")
    print("-" * 64)
    print("  QUEUE (next 3 pending)")
    print("-" * 64)
    queue = state.get("queue") or []
    pending = [q for q in queue if isinstance(q, dict) and q.get("status") == "pending"]
    if not pending:
        print("  (no pending items)")
        return
    for i, item in enumerate(pending[:3], start=1):
        slug = item.get("id", "?")
        hitl = bool(item.get("hitl", False))
        hitl_tag = "HITL" if hitl else "auto"
        deck_file = item.get("deck_file") or "(no deck file)"
        print("  %d. %-32s [%s]" % (i, slug, hitl_tag))
        print("       deck: %s" % deck_file)


def _blocker_candidate(blocker):
    """Best-effort extraction of a candidate id from a blocker record."""
    return _first_present(
        blocker, ["candidate", "candidate_id", "id", "deck", "deck_slug"]
    )


def _blocker_resolution(blocker):
    """Best-effort extraction of a suggested resolution string from a blocker."""
    return _first_present(
        blocker,
        ["resolution", "suggested_resolution", "suggested", "fix", "remedy", "action"],
    )


def _print_blockers(state):
    print("")
    print("-" * 64)
    print("  ACTIVE BLOCKERS")
    print("-" * 64)
    blockers = state.get("blockers") or []
    if not blockers:
        print("  (none)")
        return
    for i, b in enumerate(blockers, start=1):
        if not isinstance(b, dict):
            print("  %d. %s" % (i, b))
            continue
        btype = b.get("type") or b.get("kind") or "blocker"
        msg = b.get("message") or b.get("detail") or b.get("reason") or ""
        cand = _blocker_candidate(b)
        line = "  %d. type=%s" % (i, btype)
        if cand is not None:
            line += "  candidate=%s" % cand
        print(line)
        if msg:
            print("       detail: %s" % msg)
        res = _blocker_resolution(b)
        if res:
            print("       suggested: %s" % res)


def _find_steer_history(state):
    """Look for an applied-steer history under several plausible keys.

    The base schema does not define a steer-history list, so we probe the keys
    an ARL writer might use. Returns a list (possibly empty).
    """
    for key in (
        "steer_history",
        "steer_log",
        "applied_steers",
        "steers_applied",
        "steers",
    ):
        val = state.get(key)
        if isinstance(val, list) and val:
            return val
    return []


def _print_last_steer(state):
    print("")
    print("-" * 64)
    print("  LAST APPLIED STEER")
    print("-" * 64)
    history = _find_steer_history(state)
    if history:
        last = history[-1]
        if isinstance(last, dict):
            directive = _first_present(
                last, ["directive", "steer", "text", "message", "directive_text"], "?"
            )
            when = _first_present(last, ["applied_at", "at", "timestamp", "ts", "when"])
            line = '  "%s"' % directive
            if when:
                line += "  (applied %s)" % when
            print(line)
        else:
            print('  "%s"' % last)
    else:
        print("  (no applied steer recorded)")

    # Also surface anything still waiting in the steer queue, for context.
    pending = state.get("steer_queue") or []
    if pending:
        print("  pending steer_queue (%d):" % len(pending))
        for d in pending[:5]:
            if isinstance(d, dict):
                d = _first_present(d, ["directive", "steer", "text", "message"], str(d))
            print("    - %s" % d)


def _print_hitl_review(state):
    """If paused for an hitl_review blocker, print candidate id + resume line."""
    if state.get("status") != "paused":
        return
    blockers = state.get("blockers") or []
    hitl_blockers = [
        b
        for b in blockers
        if isinstance(b, dict)
        and (b.get("type") == "hitl_review" or b.get("kind") == "hitl_review")
    ]
    if not hitl_blockers:
        return
    print("")
    print("-" * 64)
    print("  HUMAN REVIEW REQUIRED")
    print("-" * 64)
    for b in hitl_blockers:
        cand = _blocker_candidate(b)
        if cand is None:
            cand = "(unknown candidate)"
        print("  candidate: %s" % cand)
    print("  review candidate, then: python scripts/arl_steer.py resume")


# --- Main ----------------------------------------------------------------------
def main():
    # Import arl_state lazily and guarded so this script degrades gracefully
    # (and always exits 0) even if the module or state cannot be loaded.
    try:
        import arl_state
    except Exception as exc:  # noqa: BLE001
        print("ARL STATUS: could not import arl_state (%s)" % exc)
        print("Is scripts/arl_state.py present? Nothing to report.")
        return 0

    try:
        state = arl_state.load_state()
    except Exception as exc:  # noqa: BLE001
        print("ARL STATUS: could not load loop state (%s)" % exc)
        return 0

    if not isinstance(state, dict):
        print("ARL STATUS: loop state is not a dict; nothing to report.")
        return 0

    _print_header(state)
    _print_promoted(state)
    _print_queue(state)
    _print_blockers(state)
    _print_last_steer(state)
    _print_hitl_review(state)
    return 0


if __name__ == "__main__":
    # Exit 0 always (read-only status tool). Catch anything unexpected.
    try:
        sys.exit(main() or 0)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print("ARL STATUS: unexpected error (%s)" % exc)
        sys.exit(0)
