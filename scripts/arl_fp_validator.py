#!/usr/bin/env python3
"""arl_fp_validator.py -- skeptical false-positive memory + promote validator.

PURPOSE
=======
The ARL (Autonomous Research Loop) generates candidate decks, gauntlet-tests
them, and promotes the ones that clear threshold. Across sessions, the loop can
re-generate a deck/claim it has *already* judged spurious (a measurement
artifact, an engine-fidelity false positive, a flake that did not replicate) and
re-promote it -- burning iterations on a verdict that was already overturned.

This module is a persistent, skeptical memory of those false positives plus a
last-mile validator the loop calls right before it promotes. Idea borrowed from
mythos-research's "skeptical memory"; this is an in-house, stdlib-only build.

It is JSON-backed at ``data/arl_false_positives.json`` (relative to the mtg-sim
repo root). The file is created LAZILY on the first ``record_false_positive``;
nothing touches the filesystem at import time.

PUBLIC API
==========
    signature(finding)                          -> str   stable, order-independent hash
    is_known_false_positive(finding, store_path=None) -> bool
    record_false_positive(finding, reason, store_path=None) -> None  (dedups)
    validate_promote(result, store_path=None)   -> (ok: bool, reason: str)

A "finding" (or "result") is the loop_state result/queue dict shape: it carries
a deck slug (under ``slug``/``id``/``deck``) and a claim (``mechanic`` and/or
``verdict``). validate_promote additionally reads ``fwr`` and ``confidence``.

CONVENTIONS
===========
ASCII-only terminal output. Run with PYTHONIOENCODING=utf-8. Exit 0 on all
self-tests passing, 1 otherwise.
"""

import os
import json
import hashlib
import tempfile
from pathlib import Path

# --- Repo-root resolution (no import-time filesystem writes) -------------------
# scripts/ lives directly under the mtg-sim repo root.
SIM_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STORE_PATH = SIM_ROOT / "data" / "arl_false_positives.json"

# Confidence buckets that must never be promoted (engine-fidelity gate). Mirrors
# arl_state.QUALITY_VOCAB / arl_distill's distillable set: only high+medium are
# trustworthy, so low + unmodelable are hard-rejected here.
UNTRUSTWORTHY_CONFIDENCE = frozenset({"low", "unmodelable"})

# Keys a deck slug may live under, in priority order.
_SLUG_KEYS = ("slug", "id", "deck", "deck_slug")
# Keys that together form "the claim" being asserted about that deck. Both are
# folded into the signature so e.g. a "promote" verdict and a "mechanic" claim on
# the same slug get distinct signatures.
_CLAIM_KEYS = ("mechanic", "verdict", "claim")


def _norm(value):
    """Normalize a scalar to a stable, comparable string ('' for missing)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip().lower()
    return str(value).strip().lower()


def _slug_of(finding):
    """Extract the deck slug from a finding, trying the known key aliases."""
    if not isinstance(finding, dict):
        return ""
    for key in _SLUG_KEYS:
        if key in finding and _norm(finding.get(key)):
            return _norm(finding.get(key))
    return ""


def _claim_pairs(finding):
    """Return the order-independent (key, normalized_value) claim pairs.

    Only non-empty claim fields are included so adding an empty/absent field
    never changes the signature.
    """
    if not isinstance(finding, dict):
        return []
    pairs = []
    for key in _CLAIM_KEYS:
        val = _norm(finding.get(key))
        if val:
            pairs.append((key, val))
    return pairs


def signature(finding: dict) -> str:
    """Stable, order-independent signature of a finding.

    The signature is a sha256 over the deck slug plus the sorted set of claim
    (key=value) pairs. Sorting makes it independent of dict insertion order and
    of which claim fields are present; two findings with the same slug + same
    claim content hash identically regardless of ordering.
    """
    slug = _slug_of(finding)
    pairs = sorted(_claim_pairs(finding))
    # Canonical, delimiter-separated payload. '|' and '=' are reserved here; the
    # normalized values are lowercased free text but the structure is fixed.
    payload = "slug=" + slug
    for key, val in pairs:
        payload += "|" + key + "=" + val
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --- Store I/O (lazy; tolerant of missing/corrupt files) ----------------------
def _resolve_store(store_path):
    """Return a Path for the store, defaulting to DEFAULT_STORE_PATH."""
    if store_path is None:
        return Path(DEFAULT_STORE_PATH)
    return Path(store_path)


def _load_store(store_path):
    """Read the FP store. Missing or corrupt -> a fresh empty store.

    Always returns a dict shaped {"false_positives": [...]}.
    """
    path = _resolve_store(store_path)
    if not path.exists():
        return {"false_positives": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except (OSError, ValueError):
        return {"false_positives": []}
    if not isinstance(loaded, dict):
        return {"false_positives": []}
    items = loaded.get("false_positives")
    if not isinstance(items, list):
        loaded["false_positives"] = []
    return loaded


def _atomic_write_json(path, data):
    """Atomically write data as JSON to path (temp file + os.replace)."""
    path = Path(path)
    directory = path.parent
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".arl_fp.", suffix=".tmp", dir=str(directory))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _known_signatures(store):
    """Set of signatures currently recorded in the store."""
    out = set()
    for entry in store.get("false_positives", []):
        if isinstance(entry, dict):
            sig = entry.get("signature")
            if isinstance(sig, str) and sig:
                out.add(sig)
    return out


# --- Public API ----------------------------------------------------------------
def is_known_false_positive(finding: dict, store_path=None) -> bool:
    """True if this finding's signature was previously recorded as an FP."""
    sig = signature(finding)
    store = _load_store(store_path)
    return sig in _known_signatures(store)


def record_false_positive(finding: dict, reason: str, store_path=None) -> None:
    """Record a finding as a known false positive. Dedups by signature.

    Creates the store file lazily on first call. If the signature is already
    present this is a no-op (the original reason/record is kept).
    """
    sig = signature(finding)
    path = _resolve_store(store_path)
    store = _load_store(path)
    if sig in _known_signatures(store):
        return
    entry = {
        "signature": sig,
        "slug": _slug_of(finding),
        "claim": dict(sorted(_claim_pairs(finding))),
        "reason": _norm(reason) if reason is not None else "",
    }
    store.setdefault("false_positives", []).append(entry)
    _atomic_write_json(path, store)


def _fwr_implausible(result):
    """True if the result's fwr is missing or outside the [0, 100] range."""
    if not isinstance(result, dict):
        return True
    fwr = result.get("fwr")
    if isinstance(fwr, bool) or not isinstance(fwr, (int, float)):
        return True
    return fwr < 0 or fwr > 100


def validate_promote(result: dict, store_path=None):
    """Gate a promote. Returns (ok: bool, reason: str).

    Rejects (ok=False) if, in order:
      1. the result's signature is a known false positive,
      2. fwr is implausible (missing/non-numeric or <0 or >100),
      3. confidence is in {"low", "unmodelable"}.
    Otherwise returns (True, "ok").
    """
    if is_known_false_positive(result, store_path=store_path):
        return (False, "known_false_positive")
    if _fwr_implausible(result):
        fwr = result.get("fwr") if isinstance(result, dict) else None
        return (False, "implausible_fwr:%r" % (fwr,))
    conf = _norm(result.get("confidence")) if isinstance(result, dict) else ""
    if conf in UNTRUSTWORTHY_CONFIDENCE:
        return (False, "untrustworthy_confidence:%s" % conf)
    return (True, "ok")


# --- Self-test -----------------------------------------------------------------
def _run_self_test():
    """Run isolated self-tests against a temp store. Returns (passed, lines)."""
    lines = []
    ok_all = True

    def check(name, cond, detail=""):
        nonlocal ok_all
        if cond:
            lines.append("PASS: %s" % name)
        else:
            ok_all = False
            lines.append("FAIL: %s%s" % (name, (" -- " + detail) if detail else ""))

    tmpdir = tempfile.mkdtemp(prefix="arl_fp_test_")
    store = os.path.join(tmpdir, "arl_false_positives.json")

    try:
        # 1. No filesystem side effect from a pure signature/query path.
        spurious = {"slug": "azorius_phantom", "mechanic": "hidden_information",
                    "verdict": "promote"}
        check("store_not_created_at_import_or_query",
              not os.path.exists(store) and not is_known_false_positive(spurious, store),
              "query touched the store file")

        # 2. signature is deterministic and order-independent.
        a = {"slug": "deck_x", "mechanic": "counters", "verdict": "promote"}
        b = {"verdict": "promote", "slug": "deck_x", "mechanic": "counters"}
        check("signature_order_independent", signature(a) == signature(b),
              "%s != %s" % (signature(a)[:12], signature(b)[:12]))
        c = {"slug": "deck_x", "mechanic": "counters", "verdict": "discard"}
        check("signature_distinguishes_claim", signature(a) != signature(c))

        # 3. record an FP -> is_known_false_positive True.
        record_false_positive(spurious, "did not replicate at N=200", store)
        check("store_created_lazily_on_record", os.path.exists(store))
        check("recorded_fp_is_known", is_known_false_positive(spurious, store))

        # 4. dedup by signature (re-record same claim, different field order).
        reordered = {"verdict": "promote", "mechanic": "hidden_information",
                     "slug": "azorius_phantom"}
        record_false_positive(reordered, "still spurious", store)
        with open(store, "r", encoding="utf-8") as f:
            data = json.load(f)
        check("record_dedups_by_signature",
              len(data["false_positives"]) == 1,
              "expected 1 entry, got %d" % len(data["false_positives"]))

        # 5. a fresh finding -> not known + validate_promote ok.
        fresh = {"slug": "boros_energy", "verdict": "promote", "fwr": 62.4,
                 "confidence": "high"}
        check("fresh_finding_not_known", not is_known_false_positive(fresh, store))
        ok, reason = validate_promote(fresh, store)
        check("fresh_finding_validates", ok and reason == "ok", "reason=%s" % reason)

        # 6. validate_promote rejects a known FP.
        known_result = dict(spurious)
        known_result.update({"fwr": 61.0, "confidence": "high"})
        ok, reason = validate_promote(known_result, store)
        check("validate_rejects_known_fp",
              (not ok) and reason == "known_false_positive", "reason=%s" % reason)

        # 7. implausible fwr -> rejected (both > 100 and < 0 and missing).
        for bad_fwr, tag in ((140.0, "over_100"), (-5.0, "below_0"), (None, "missing")):
            r = {"slug": "deck_%s" % tag, "verdict": "promote",
                 "fwr": bad_fwr, "confidence": "high"}
            ok, reason = validate_promote(r, store)
            check("validate_rejects_implausible_fwr_%s" % tag,
                  (not ok) and reason.startswith("implausible_fwr"),
                  "ok=%s reason=%s" % (ok, reason))

        # 8. untrustworthy confidence -> rejected.
        for conf in ("low", "unmodelable"):
            r = {"slug": "deck_conf_%s" % conf, "verdict": "promote",
                 "fwr": 65.0, "confidence": conf}
            ok, reason = validate_promote(r, store)
            check("validate_rejects_confidence_%s" % conf,
                  (not ok) and reason == "untrustworthy_confidence:%s" % conf,
                  "ok=%s reason=%s" % (ok, reason))

        # 9. corrupt store is tolerated (reads as empty, no crash).
        with open(store, "w", encoding="utf-8") as f:
            f.write("{not valid json")
        check("corrupt_store_tolerated", not is_known_false_positive(spurious, store))

    finally:
        try:
            if os.path.exists(store):
                os.remove(store)
            os.rmdir(tmpdir)
        except OSError:
            pass

    return ok_all, lines


if __name__ == "__main__":
    import sys

    passed, report = _run_self_test()
    for line in report:
        print(line)
    print("RESULT: %s" % ("ALL PASS" if passed else "FAILURES PRESENT"))
    sys.exit(0 if passed else 1)
