#!/usr/bin/env python3
"""arl_state.py -- single owner of loop_state.json for the ARL loop.

This is the interface CONTRACT every other ARL script depends on. All reads and
writes of loop_state.json MUST go through the helpers here so the schema stays
stable and writes stay Ctrl-C-safe (atomic).

Public API:
    STATE_PATH                      absolute path to loop_state.json
    BACKLOG_PATH                    absolute path to modelability_backlog.json
    default_state()  -> dict        freshly seeded schema
    load_state()     -> dict        read+merge from disk (tolerant)
    write_state(s)   -> None        stamp last_updated + atomic persist
    new_queue_item(...) -> dict     queue item factory
    new_result(...)     -> dict     result factory
    new_backlog_item(...) -> dict   modelability backlog item factory
    load_backlog()   -> dict        read modelability backlog (tolerant)
    append_backlog(item) -> None    atomic append, dedup by slug+mechanic

HITL note (HANDOFF-04 task 3.3): every queue item and result carries an "hitl"
boolean (default False).

Data-quality note (archetype-capability-profiles spec, 2026-06-26): every result
carries data_quality + confidence (each in {high, medium, low, unmodelable},
default "high") and blocking_imperfections (list, default []). The
engine-fidelity gate uses these to decide promote vs low_confidence vs
unmodelable. "unmodelable" results enqueue a replication target to the
modelability backlog -- a real work item, never a silent dead-end.
"""

import os
import sys
import json
import tempfile
from datetime import datetime, timezone

# --- Cross-repo sys.path setup -------------------------------------------------
SIM_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_SCRIPTS = os.path.abspath(
    os.path.join(SIM_ROOT, "..", "harness", "agents", "scripts")
)
for _p in (SIM_ROOT, HARNESS_SCRIPTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# --- Constants -----------------------------------------------------------------
STATE_PATH = os.path.join(SIM_ROOT, "loop_state.json")
BACKLOG_PATH = os.path.join(SIM_ROOT, "data", "modelability_backlog.json")

DEFAULT_PROMOTE_THRESHOLD = 60.0

# Controlled vocabulary shared by data_quality + confidence. Anything outside
# this set is coerced to "low" so the gate fails safe (never silently "high").
QUALITY_VOCAB = ("high", "medium", "low", "unmodelable")


def _coerce_quality(value, default="high"):
    """Normalize a data_quality/confidence string to QUALITY_VOCAB.

    Unknown / non-string values fall back to `default` for empty input but to
    "low" for an actual out-of-vocab value, so a typo can never read as "high".
    """
    if value is None or value == "":
        return default
    if isinstance(value, str):
        v = value.strip().lower()
        if v in QUALITY_VOCAB:
            return v
    return "low"


# --- Time helper ---------------------------------------------------------------
def _utc_now_iso():
    """Current UTC time as ISO8601. Deterministic format, no locale surprises."""
    return datetime.now(timezone.utc).isoformat()


# --- Schema --------------------------------------------------------------------
def default_state():
    """Return a fresh loop_state schema seeded with idle defaults."""
    return {
        "status": "idle",
        "mode": "explore",
        "target_format": "modern",
        "iteration": 0,
        "queue": [],
        "results": [],
        "promoted": [],
        "steer_queue": [],
        "blockers": [],
        "promote_threshold": DEFAULT_PROMOTE_THRESHOLD,
        "last_updated": _utc_now_iso(),
    }


def _merge_onto_default(loaded):
    """Merge a (possibly partial/old) loaded dict onto a fresh default.

    Unknown keys from disk are preserved; missing keys are backfilled from the
    default schema. This tolerates schema drift in both directions.
    """
    state = default_state()
    if isinstance(loaded, dict):
        state.update(loaded)
    return state


# --- Atomic write helper -------------------------------------------------------
# Prefer a shared helper from agent_hardening if one exists; otherwise fall back
# to an inline atomic write. The import is guarded so read-only use and --help
# work even if the harness module is missing.
try:  # pragma: no cover - depends on harness layout
    from agent_hardening import atomic_write_json as _atomic_write_json  # type: ignore
except Exception:  # noqa: BLE001 - any import failure -> inline fallback
    _atomic_write_json = None


def _inline_atomic_write_json(path, data):
    """Atomically write `data` as JSON to `path` (Ctrl-C-safe).

    Strategy: write to a temp file in the same directory, flush + fsync, then
    os.replace() onto the final path (atomic on the same filesystem).
    """
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".arl_state.", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        # Best-effort cleanup of the temp file on failure.
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise


# --- Public I/O ----------------------------------------------------------------
def load_state():
    """Read loop_state.json. On missing/corrupt file, return default_state().

    Missing keys are tolerated by merging the loaded dict onto a fresh default.
    """
    if not os.path.exists(STATE_PATH):
        return default_state()
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except (OSError, ValueError):
        # Corrupt/unreadable JSON -> fall back to clean default.
        return default_state()
    return _merge_onto_default(loaded)


def _persist_json(path, data):
    """Atomically write `data` to `path`, preferring the shared harness helper."""
    if _atomic_write_json is not None:
        _atomic_write_json(path, data)
    else:
        _inline_atomic_write_json(path, data)


def write_state(state):
    """Stamp last_updated (UTC ISO8601) and atomically persist to STATE_PATH."""
    if not isinstance(state, dict):
        raise TypeError("write_state expects a dict, got %r" % type(state).__name__)
    state["last_updated"] = _utc_now_iso()
    _persist_json(STATE_PATH, state)


# --- Factories -----------------------------------------------------------------
def new_queue_item(id, deck_file=None, apl_file=None, hitl=False, notes=""):
    """Build a queue item. status starts 'pending', fwr unknown (None)."""
    return {
        "id": id,
        "deck_file": deck_file,
        "apl_file": apl_file,
        "status": "pending",
        "fwr": None,
        "hitl": bool(hitl),
        "notes": notes,
    }


def new_result(id, deck_file, fwr, vs_field, hypothesis, verdict, hitl=False,
               notes="", data_quality="high", confidence="high",
               blocking_imperfections=None):
    """Build a result record. vs_field defaults to {} if falsy.

    Engine-fidelity fields (archetype-capability-profiles spec):
      data_quality            "high" | "medium" | "low" | "unmodelable"
      confidence              same vocab; the gate keys off this
      blocking_imperfections  list of imperfection ids that gate the result

    Backward compatible: callers that omit the new kwargs get the safe
    defaults (high / high / []). Out-of-vocab strings coerce to "low" so a
    typo can never read as trustworthy "high".
    """
    if blocking_imperfections is None:
        bi = []
    elif isinstance(blocking_imperfections, (list, tuple)):
        bi = list(blocking_imperfections)
    else:
        bi = [blocking_imperfections]
    return {
        "id": id,
        "deck_file": deck_file,
        "fwr": fwr,
        "vs_field": vs_field if vs_field else {},
        "hypothesis": hypothesis,
        "verdict": verdict,
        "hitl": bool(hitl),
        "notes": notes,
        "data_quality": _coerce_quality(data_quality, default="high"),
        "confidence": _coerce_quality(confidence, default="high"),
        "blocking_imperfections": bi,
    }


# --- Modelability backlog ------------------------------------------------------
# "unmodelable" gate verdicts enqueue a real engine-capability work item here
# (file: data/modelability_backlog.json, shape {"items": []}). Each item names
# the mechanic the engine can't yet represent, the imperfection that blocks it,
# a field_share*win_impact priority (or null), and a real-world replication
# target the engine must reproduce + PROVE once the mechanic is modeled.
def new_backlog_item(slug, archetype, mechanic, blocking_imperfection,
                     priority=None, real_wr=None, known_line="", created=None):
    """Build a modelability backlog item with the spec's required shape."""
    return {
        "slug": slug,
        "archetype": archetype,
        "mechanic": mechanic,
        "blocking_imperfection": blocking_imperfection,
        "priority": priority,  # field_share*win_impact if known, else None
        "replication_target": {
            "real_wr": real_wr,        # null-or-float: real tournament WR to hit
            "known_line": known_line,  # at least one winning line to reproduce
        },
        "created": created or _utc_now_iso(),
    }


def _default_backlog():
    """Fresh empty backlog with the canonical {"items": []} shape."""
    return {"items": []}


def load_backlog():
    """Read modelability_backlog.json. Tolerant: missing/corrupt -> empty.

    Always returns a dict with an "items" list, even if the on-disk file is
    malformed or has the wrong top-level shape.
    """
    if not os.path.exists(BACKLOG_PATH):
        return _default_backlog()
    try:
        with open(BACKLOG_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except (OSError, ValueError):
        return _default_backlog()
    if not isinstance(loaded, dict):
        return _default_backlog()
    items = loaded.get("items")
    if not isinstance(items, list):
        loaded["items"] = []
    return loaded


def _backlog_key(item):
    """Dedup key for a backlog item: (slug, mechanic)."""
    if not isinstance(item, dict):
        return (None, None)
    return (item.get("slug"), item.get("mechanic"))


def append_backlog(item):
    """Atomically append a backlog item, dedup by (slug, mechanic).

    If an item with the same slug+mechanic already exists, this is a no-op
    (the existing item -- including its created stamp -- is preserved). Missing
    required fields are backfilled so callers can pass a partial dict.
    """
    if not isinstance(item, dict):
        raise TypeError("append_backlog expects a dict, got %r"
                        % type(item).__name__)

    # Backfill required shape from a fresh factory item so partial dicts work.
    normalized = new_backlog_item(
        slug=item.get("slug"),
        archetype=item.get("archetype"),
        mechanic=item.get("mechanic"),
        blocking_imperfection=item.get("blocking_imperfection"),
        priority=item.get("priority"),
        created=item.get("created"),
    )
    # Preserve a caller-supplied replication_target if present + well-formed.
    rt = item.get("replication_target")
    if isinstance(rt, dict):
        normalized["replication_target"] = {
            "real_wr": rt.get("real_wr"),
            "known_line": rt.get("known_line", "") or "",
        }
    # Carry over any extra caller keys (don't clobber the normalized ones).
    for k, v in item.items():
        if k not in normalized:
            normalized[k] = v

    backlog = load_backlog()
    key = _backlog_key(normalized)
    for existing in backlog["items"]:
        if _backlog_key(existing) == key:
            return  # already queued -- dedup, no duplicate work item
    backlog["items"].append(normalized)
    _persist_json(BACKLOG_PATH, backlog)


# --- CLI (read-only) -----------------------------------------------------------
if __name__ == "__main__":
    print("ARL state path: %s" % STATE_PATH)
    print("Exists: %s" % os.path.exists(STATE_PATH))
    print("Backlog path: %s" % BACKLOG_PATH)
    print("Backlog exists: %s" % os.path.exists(BACKLOG_PATH))
    sys.exit(0)
