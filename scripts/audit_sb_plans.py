"""Audit MATCHUP_SB_PLANS across every match APL.

For each (apl, matchup, plan):
  - Parse IN/OUT card lists (qty + name)
  - Verify OUT cards exist in mainboard with >= requested qty
  - Verify IN cards exist in sideboard with >= requested qty
  - Verify IN/OUT counts balance (same total)
  - Report plans with issues

Run: python scripts/audit_sb_plans.py [--verbose]
"""
import sys, os, importlib, pkgutil, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apl import APL_REGISTRY, MATCH_APL_REGISTRY, get_match_apl
from data.deck import load_deck_from_file
from engine.sideboard import parse_sb_string


def audit_plan(apl, opp_key, plan, deck, sb):
    """Return list of issue strings for a single plan."""
    issues = []
    sb_in_raw, sb_out_raw = plan
    if not sb_in_raw and not sb_out_raw:
        return []  # explicit no-sideboard plan

    main_counts = collections.Counter(c.name for c in deck)
    sb_counts = collections.Counter(c.name for c in sb)

    in_total = 0
    for raw in sb_in_raw:
        for qty, name in parse_sb_string(raw):
            in_total += qty
            available = sb_counts.get(name, 0)
            if available == 0:
                issues.append(f"  IN {qty}x {name!r} -- NOT IN SIDEBOARD")
            elif qty > available:
                issues.append(f"  IN {qty}x {name!r} -- only {available} in SB")

    out_total = 0
    for raw in sb_out_raw:
        for qty, name in parse_sb_string(raw):
            out_total += qty
            available = main_counts.get(name, 0)
            if available == 0:
                issues.append(f"  OUT {qty}x {name!r} -- NOT IN MAIN")
            elif qty > available:
                issues.append(f"  OUT {qty}x {name!r} -- only {available} in main")

    if in_total != out_total:
        issues.append(f"  COUNT MISMATCH: {in_total} IN vs {out_total} OUT")

    return issues


def main():
    verbose = "--verbose" in sys.argv
    total_apls = 0
    total_plans = 0
    apls_with_issues = 0
    plans_with_issues = 0
    issue_lines = []

    for key in sorted(MATCH_APL_REGISTRY.keys()):
        try:
            apl = get_match_apl(key)
        except Exception as e:
            issue_lines.append(f"{key}: cannot instantiate ({e})")
            continue

        plans = getattr(apl, "MATCHUP_SB_PLANS", None)
        if not plans:
            continue
        # Find decklist path from APL_REGISTRY
        if key not in APL_REGISTRY:
            continue
        deck_path = APL_REGISTRY[key][2]
        try:
            deck, sb = load_deck_from_file(deck_path)
        except Exception as e:
            issue_lines.append(f"{key}: cannot load deck {deck_path} ({e})")
            continue

        total_apls += 1
        apl_issues = []
        for opp_key, plan in plans.items():
            if plan is None:
                continue
            total_plans += 1
            issues = audit_plan(apl, opp_key, plan, deck, sb)
            if issues:
                plans_with_issues += 1
                apl_issues.append((opp_key, issues))

        if apl_issues:
            apls_with_issues += 1
            issue_lines.append(f"\n=== {key} ({len(apl_issues)} broken plans) ===")
            for opp_key, issues in apl_issues:
                issue_lines.append(f"\n  matchup: {opp_key}")
                for line in issues:
                    issue_lines.append(line)
        elif verbose:
            issue_lines.append(f"\n=== {key} OK ({len(plans)} plans) ===")

    print(f"Audited {total_apls} match APLs, {total_plans} plans total")
    print(f"APLs with issues: {apls_with_issues}")
    print(f"Plans with issues: {plans_with_issues}")
    if issue_lines:
        print("\n" + "\n".join(issue_lines))


if __name__ == "__main__":
    main()
