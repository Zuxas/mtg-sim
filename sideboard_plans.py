"""
sideboard_plans.py -- pick a sideboard plan for a Bo3 and refuse anything that isn't
a legal, exact card swap.

Why (2026-09-29, spec harness/specs/2026-09-30-sideboard-plan-validation.md): the
launcher used playbook plans applied by engine.sideboard.apply_sideboard_plan, which
fuzzy-matches names, silently skips unknown cards and never checks deck size. On the
Modern + Standard fields no plan produced a legal changed deck (Standard: 57/59/62
cards), yet every non-empty plan was reported as sb_mode "real".

A plan is (sb_in_lines, sb_out_lines) of 'N Card Name' strings. It is used only if
every line parses, every name is an exact card in our sideboard (in) / main (out) with
enough copies, cards in == cards out > 0, and the engine's applier produces exactly
that swap.
"""
from __future__ import annotations

from collections import Counter

from engine.sideboard import apply_sideboard_plan, get_sb_plan, parse_sb_string


def _parse(lines) -> tuple[Counter | None, str]:
    out: Counter = Counter()
    for raw in lines or []:
        parsed = parse_sb_string(raw)
        if not parsed:
            return None, f"unparsable line {raw!r}"
        for qty, name in parsed:
            out[name] += qty
    return out, ""


def _exact(name: str, pool: Counter) -> str | None:
    low = name.lower().strip()
    for n in pool:
        if n.lower() == low:
            return n
    return None


def validate_plan(main: list, side: list, sb_in, sb_out) -> tuple[bool, str, dict]:
    """(ok, reason, {"in": Counter, "out": Counter}) for a plan against our 60 + 15."""
    ins, why = _parse(sb_in)
    if ins is None:
        return False, why, {}
    outs, why = _parse(sb_out)
    if outs is None:
        return False, why, {}
    if not ins and not outs:
        return False, "empty plan", {}
    main_c = Counter(c.name for c in main)
    side_c = Counter(c.name for c in side)
    swap_in, swap_out = Counter(), Counter()
    for name, qty in ins.items():
        exact = _exact(name, side_c)
        if exact is None:
            return False, f"sb_in card not in our sideboard: {name!r}", {}
        swap_in[exact] += qty
    for name, qty in outs.items():
        exact = _exact(name, main_c)
        if exact is None:
            return False, f"sb_out card not in our main: {name!r}", {}
        swap_out[exact] += qty
    for name, qty in swap_in.items():
        if qty > side_c[name]:
            return False, f"sb_in wants {qty} {name!r}, sideboard has {side_c[name]}", {}
    for name, qty in swap_out.items():
        if qty > main_c[name]:
            return False, f"sb_out wants {qty} {name!r}, main has {main_c[name]}", {}
    n_in, n_out = sum(swap_in.values()), sum(swap_out.values())
    if n_in != n_out:
        return False, f"{n_in} in vs {n_out} out", {}
    expected = main_c - swap_out + swap_in
    got = Counter(c.name for c in apply_sideboard_plan(main, side, list(sb_in or []), list(sb_out or [])))
    if got != expected:
        return False, "engine applier result differs from the exact swap (fuzzy match)", {}
    return True, f"{n_in}-for-{n_out}", {"in": swap_in, "out": swap_out}


def choose_plan(our_key: str, opp_key: str, main: list, side: list,
                our_apl=None, opp_apl=None) -> tuple[tuple | None, str, str]:
    """(plan or None, source, reason). Candidates: our APL's SB_PLANS for the opponent's
    ARCHETYPE, then the playbook plan. First valid wins."""
    candidates = []
    if our_apl is not None and hasattr(our_apl, "sb_plan_for") and opp_apl is not None:
        p = our_apl.sb_plan_for(getattr(opp_apl, "ARCHETYPE", ""))
        if p:
            candidates.append(("apl", p))
    pin, pout = get_sb_plan(our_key, opp_key)
    if pin or pout:
        candidates.append(("playbook", (list(pin), list(pout))))
    if not candidates:
        return None, "none", "no plan"
    reasons = []
    for source, plan in candidates:
        ok, why, _ = validate_plan(main, side, plan[0], plan[1])
        if ok:
            return (list(plan[0]), list(plan[1])), source, why
        reasons.append(f"{source}: {why}")
    return None, "rejected", "; ".join(reasons)
