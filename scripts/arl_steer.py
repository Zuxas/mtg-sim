#!/usr/bin/env python3
"""arl_steer.py -- inject a steer directive into the ARL loop.

Usage:
    python arl_steer.py "<directive>"

Every directive is appended verbatim to loop_state.json's steer_queue as
{"directive": <str>, "ts": <utc iso>}; the running loop interprets it at its
next clean iteration boundary. A few directives also get an immediate-effect
shortcut applied here so a *paused* loop (which is not executing iterations and
therefore cannot drain the steer_queue itself) can still react:

    "resume"                    -> set status="running" right now
    "pause"                     -> append-only; the loop honors it at its next
                                   boundary (we do NOT mid-write status here
                                   beyond the queue entry)
    "set promote_threshold to N" -> store float N in state["promote_threshold"]
    "flag <id> for review"      -> set hitl=true on that id in queue and/or
                                   promoted (both are searched)

All other directives are stored verbatim for the loop to interpret.

ASCII-only output. Exit 0 on success, 1 on error.
"""

import os
import re
import sys
from datetime import datetime, timezone

# --- Cross-repo sys.path setup -------------------------------------------------
SIM_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_SCRIPTS = os.path.abspath(
    os.path.join(SIM_ROOT, "..", "harness", "agents", "scripts")
)
for _p in (SIM_ROOT, HARNESS_SCRIPTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import arl_state  # noqa: E402  (path setup must run first)


def _utc_now_iso():
    """Current UTC time as ISO8601 (matches arl_state's stamp format)."""
    return datetime.now(timezone.utc).isoformat()


def _flag_for_review(state, target_id):
    """Set hitl=true on any item matching target_id in queue and/or promoted.

    Both collections are searched. queue items are dicts (keyed by "id").
    promoted entries may be plain deck-slug strings (per the documented schema)
    or dicts; for dict entries we can set the hitl flag, for string entries we
    record a match but cannot attach a flag (no field to set). Returns a list of
    human-readable location strings describing where the flag was applied or a
    bare match was found.
    """
    hits = []

    def _scan(collection, label):
        for item in collection:
            if isinstance(item, dict) and item.get("id") == target_id:
                item["hitl"] = True
                hits.append("%s (hitl set)" % label)
            elif isinstance(item, str) and item == target_id:
                # promoted is documented as a list of slug strings; nothing to
                # flag on a bare string, but report the match so it is visible.
                hits.append("%s (matched, no dict to flag)" % label)

    _scan(state.get("queue", []), "queue")
    _scan(state.get("promoted", []), "promoted")
    return hits


def apply_directive(state, directive):
    """Mutate `state` for any immediate-effect directive. Returns a list of
    applied-effect description strings (empty if directive is store-only)."""
    applied = []
    norm = directive.strip().lower()

    # "resume" -> flip status immediately so a paused loop comes back to life.
    if norm == "resume":
        state["status"] = "running"
        applied.append("status set to running (resume)")
        return applied

    # "pause" -> append-only here; the loop sets status=paused at its next
    # clean boundary. We deliberately do NOT mid-write status.
    if norm == "pause":
        applied.append("pause queued (loop will honor at next boundary)")
        return applied

    # "set promote_threshold to N"
    m = re.search(r"set\s+promote_threshold\s+to\s+([0-9]*\.?[0-9]+)", norm)
    if m:
        value = float(m.group(1))
        state["promote_threshold"] = value
        applied.append("promote_threshold set to %s" % value)
        return applied

    # "flag <id> for review"
    m = re.search(r"flag\s+(\S+)\s+for\s+review", norm)
    if m:
        # Pull the id from the ORIGINAL directive to preserve case in slugs.
        m_orig = re.search(
            r"flag\s+(\S+)\s+for\s+review", directive.strip(), re.IGNORECASE
        )
        target_id = m_orig.group(1) if m_orig else m.group(1)
        hits = _flag_for_review(state, target_id)
        if hits:
            applied.append(
                "flagged '%s' for review: %s" % (target_id, ", ".join(hits))
            )
        else:
            applied.append(
                "flag '%s' for review: id not found in queue or promoted "
                "(directive stored for loop)" % target_id
            )
        return applied

    # Store-only: nothing applied immediately.
    return applied


def main(argv):
    args = [a for a in argv[1:] if a.strip()]
    if not args:
        print("ERROR: a directive is required.")
        print('Usage: python arl_steer.py "<directive>"')
        return 1

    # Join multiple shell tokens so unquoted multi-word directives still work.
    directive = " ".join(args).strip()
    if not directive:
        print("ERROR: directive is empty.")
        return 1

    state = arl_state.load_state()

    # Always record the directive verbatim for the loop to interpret.
    entry = {"directive": directive, "ts": _utc_now_iso()}
    state.setdefault("steer_queue", []).append(entry)

    # Apply any immediate-effect shortcuts.
    applied = apply_directive(state, directive)

    arl_state.write_state(state)

    print("ARL steer applied.")
    print("  state file: %s" % arl_state.STATE_PATH)
    print("  directive:  %s" % directive)
    print("  queued at:  %s" % entry["ts"])
    print("  steer_queue depth: %d" % len(state.get("steer_queue", [])))
    if applied:
        for line in applied:
            print("  immediate:  %s" % line)
    else:
        print("  immediate:  none (stored for loop to interpret)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
