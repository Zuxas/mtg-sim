"""arl_approval.py -- Tiered Action Gate for the Autonomous Research Loop (ARL).

In-house hardening module (idea borrowed from the hermes-webui approval flow;
Rule-of-Two aligned). It codifies what the autonomous loop may do unattended
versus what must be surfaced to a human.

Three tiers:
    AUTO              -- safe, reversible, local; run unattended, no flag.
    NOTIFY            -- allowed unattended but flagged for after-the-fact review.
    REQUIRE_APPROVAL  -- must NOT run unattended; needs a human in the loop.

Policy is fail-closed: any unknown action type, or any action whose target path
lives under an "engine/" directory, escalates to REQUIRE_APPROVAL.

Pure stdlib. ASCII-only output. Importable from scripts/arl_loop.py and
harness/agents/scripts/auto_pipeline.py (SIM_ROOT is on sys.path).

Public API:
    classify(action_type, target="") -> str
    gate(action_type, target="") -> (allowed_unattended, tier, reason)
"""

from __future__ import annotations

import sys
from typing import Tuple

# --- Tier constants ---------------------------------------------------------
AUTO: str = "AUTO"
NOTIFY: str = "NOTIFY"
REQUIRE_APPROVAL: str = "REQUIRE_APPROVAL"

# --- Policy map -------------------------------------------------------------
_AUTO_ACTIONS = frozenset({"sim_run", "local_file_write", "read", "gauntlet"})
_NOTIFY_ACTIONS = frozenset({"git_commit", "registry_write", "backlog_write"})
_REQUIRE_APPROVAL_ACTIONS = frozenset(
    {"git_push", "external_comms", "engine_edit", "delete", "mcp_private"}
)


def _normalize(value: str) -> str:
    """Lowercase + strip; tolerate None-ish input by coercing to str."""
    return ("" if value is None else str(value)).strip().lower()


def _targets_engine_dir(target: str) -> bool:
    """True if target path references an 'engine/' directory segment.

    Matches both forward and back slashes so Windows paths (engine\\foo) and
    POSIX paths (engine/foo) are both caught. A bare 'engine' with no following
    separator is treated as a plain name, not a directory, and does not match.
    """
    if not target:
        return False
    norm = _normalize(target).replace("\\", "/")
    # pad with leading/trailing slash so boundary checks are uniform
    padded = "/" + norm.strip("/") + "/"
    return "/engine/" in padded


def classify(action_type: str, target: str = "") -> str:
    """Return the tier (AUTO | NOTIFY | REQUIRE_APPROVAL) for an action.

    Resolution order (fail-closed):
        1. Any target under an engine/ dir -> REQUIRE_APPROVAL (overrides type).
        2. Known REQUIRE_APPROVAL action type -> REQUIRE_APPROVAL.
        3. Known NOTIFY action type           -> NOTIFY.
        4. Known AUTO action type             -> AUTO.
        5. Unknown action type                -> REQUIRE_APPROVAL.
    """
    act = _normalize(action_type)

    # Engine paths are sacred: escalate regardless of declared action type.
    if _targets_engine_dir(target):
        return REQUIRE_APPROVAL

    if act in _REQUIRE_APPROVAL_ACTIONS:
        return REQUIRE_APPROVAL
    if act in _NOTIFY_ACTIONS:
        return NOTIFY
    if act in _AUTO_ACTIONS:
        return AUTO

    # Unknown -> fail closed.
    return REQUIRE_APPROVAL


def gate(action_type: str, target: str = "") -> Tuple[bool, str, str]:
    """Decide whether an action may run unattended.

    Returns (allowed_unattended, tier, reason):
        allowed_unattended -- True only for AUTO and NOTIFY tiers.
        tier               -- the classified tier string.
        reason             -- human-readable explanation for logs/audits.

    NOTIFY is allowed unattended but the caller should flag it for review.
    REQUIRE_APPROVAL is never allowed unattended.
    """
    tier = classify(action_type, target)
    act = _normalize(action_type) or "<empty>"
    tgt = _normalize(target)

    if tier == AUTO:
        return True, AUTO, "action '%s' is AUTO: safe to run unattended" % act

    if tier == NOTIFY:
        return (
            True,
            NOTIFY,
            "action '%s' is NOTIFY: allowed unattended, flag for review" % act,
        )

    # REQUIRE_APPROVAL
    if _targets_engine_dir(target):
        reason = (
            "action '%s' targets engine dir '%s': human approval required"
            % (act, tgt)
        )
    elif act in _REQUIRE_APPROVAL_ACTIONS:
        reason = "action '%s' is REQUIRE_APPROVAL: human approval required" % act
    else:
        reason = (
            "action '%s' is unknown: fail-closed, human approval required" % act
        )
    return False, REQUIRE_APPROVAL, reason


# --- Self-test --------------------------------------------------------------
def _run_self_test() -> int:
    """Print PASS/FAIL per case; return 0 only if all pass."""
    failures = 0

    def check(label: str, got, expected) -> None:
        nonlocal failures
        if got == expected:
            print("PASS: %s" % label)
        else:
            failures += 1
            print("FAIL: %s -- expected %r, got %r" % (label, expected, got))

    # classify: tier mapping
    check("classify sim_run -> AUTO", classify("sim_run"), AUTO)
    check("classify gauntlet -> AUTO", classify("gauntlet"), AUTO)
    check("classify read -> AUTO", classify("read"), AUTO)
    check(
        "classify local_file_write -> AUTO",
        classify("local_file_write"),
        AUTO,
    )
    check("classify git_commit -> NOTIFY", classify("git_commit"), NOTIFY)
    check(
        "classify registry_write -> NOTIFY",
        classify("registry_write"),
        NOTIFY,
    )
    check(
        "classify backlog_write -> NOTIFY",
        classify("backlog_write"),
        NOTIFY,
    )
    check(
        "classify git_push -> REQUIRE_APPROVAL",
        classify("git_push"),
        REQUIRE_APPROVAL,
    )
    check(
        "classify external_comms -> REQUIRE_APPROVAL",
        classify("external_comms"),
        REQUIRE_APPROVAL,
    )
    check(
        "classify delete -> REQUIRE_APPROVAL",
        classify("delete"),
        REQUIRE_APPROVAL,
    )

    # unknown -> REQUIRE_APPROVAL (fail-closed)
    check(
        "classify unknown -> REQUIRE_APPROVAL",
        classify("frobnicate_the_widget"),
        REQUIRE_APPROVAL,
    )
    check(
        "classify empty -> REQUIRE_APPROVAL",
        classify(""),
        REQUIRE_APPROVAL,
    )

    # case/whitespace insensitivity
    check(
        "classify '  Sim_Run ' -> AUTO",
        classify("  Sim_Run "),
        AUTO,
    )

    # engine/ target escalation (overrides an otherwise-AUTO action)
    check(
        "classify local_file_write @ engine/ -> REQUIRE_APPROVAL (posix)",
        classify("local_file_write", "mtg-sim/engine/combat.py"),
        REQUIRE_APPROVAL,
    )
    check(
        "classify read @ engine\\ -> REQUIRE_APPROVAL (windows)",
        classify("read", "E:/repo/engine\\rules.py"),
        REQUIRE_APPROVAL,
    )
    check(
        "classify sim_run @ non-engine -> AUTO",
        classify("sim_run", "data/decks/aggro.json"),
        AUTO,
    )
    check(
        "classify read @ 'engineering/' is NOT engine dir -> AUTO",
        classify("read", "docs/engineering/notes.md"),
        AUTO,
    )

    # gate: allowed_unattended flag
    g_auto = gate("sim_run")
    check("gate sim_run allowed_unattended True", g_auto[0], True)
    check("gate sim_run tier AUTO", g_auto[1], AUTO)

    g_notify = gate("git_commit")
    check("gate git_commit allowed_unattended True", g_notify[0], True)
    check("gate git_commit tier NOTIFY", g_notify[1], NOTIFY)

    g_req = gate("git_push")
    check("gate git_push allowed_unattended False", g_req[0], False)
    check("gate git_push tier REQUIRE_APPROVAL", g_req[1], REQUIRE_APPROVAL)

    g_unknown = gate("totally_made_up")
    check("gate unknown allowed_unattended False", g_unknown[0], False)
    check(
        "gate unknown tier REQUIRE_APPROVAL",
        g_unknown[1],
        REQUIRE_APPROVAL,
    )

    g_engine = gate("local_file_write", "engine/state.py")
    check("gate engine target allowed_unattended False", g_engine[0], False)
    check(
        "gate engine target tier REQUIRE_APPROVAL",
        g_engine[1],
        REQUIRE_APPROVAL,
    )
    check(
        "gate engine target reason mentions engine",
        "engine" in g_engine[2],
        True,
    )

    # reason strings are non-empty for every tier
    check("gate AUTO reason non-empty", bool(g_auto[2]), True)
    check("gate NOTIFY reason non-empty", bool(g_notify[2]), True)
    check("gate REQUIRE_APPROVAL reason non-empty", bool(g_req[2]), True)

    print("")
    if failures == 0:
        print("ALL PASS")
        return 0
    print("TOTAL FAILURES: %d" % failures)
    return 1


if __name__ == "__main__":
    sys.exit(_run_self_test())
