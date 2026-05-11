"""Audit deck data + MATCHUP_SB_PLANS health across the project.

Two audit modes:
  --sb-plans (default): for each (apl, matchup, plan), verify cards exist
    in deck/sb with correct counts and IN/OUT balance
  --decks: scan every decks/*.txt for empty-oracle / unknown / banned cards
  --all: run both

Run: python scripts/audit_sb_plans.py [--sb-plans | --decks | --all] [--verbose]
"""
import sys, os, glob, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apl import APL_REGISTRY, MATCH_APL_REGISTRY, get_match_apl
from data.deck import load_deck_from_file
from engine.sideboard import parse_sb_string
from engine.card_db import CardDB, get_oracle


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


def audit_decks(verbose=False):
    """Scan every decks/*.txt for data quality issues.

    Reports:
      - Cards with empty oracle text (likely token / art-series / unknown)
      - Cards not found in card_db
      - Banned cards (Standard format only — hard-coded list)
      - Non-60 mainboards (already flagged with audit:* markers in headers)
    """
    db = CardDB()
    # Hard-coded banned-in-Standard list (as of 2026-05). Add cards here as
    # the format changes.
    BANNED_STANDARD = {
        "Cori-Steel Cutter",      # banned 2025-06-30
        "Mana Confluence",         # banned for power level
        "Detect Intrusion",        # Unhinged joke card, never legal
        "Belion",                  # Unhinged joke card
    }

    issue_lines = []
    decks_scanned = 0
    decks_with_issues = 0
    empty_oracles = collections.defaultdict(list)
    unknown_cards = collections.defaultdict(list)
    banned_finds = collections.defaultdict(list)

    for path in sorted(glob.glob("decks/*.txt")):
        try:
            deck, sb = load_deck_from_file(path)
        except Exception as e:
            issue_lines.append(f"{path}: load failed ({e})")
            continue
        decks_scanned += 1
        deck_issues = []

        # Card-level checks — dedup by name to avoid spam
        seen = set()
        for c in deck + sb:
            if c.name in seen:
                continue
            seen.add(c.name)
            card_data = db.get(c.name)
            if not card_data:
                unknown_cards[c.name].append(os.path.basename(path))
                deck_issues.append(f"  UNKNOWN: {c.name!r}")
            elif not get_oracle(c.name):
                empty_oracles[c.name].append(os.path.basename(path))
            if c.name in BANNED_STANDARD and "_standard" in path:
                banned_finds[c.name].append(os.path.basename(path))
                deck_issues.append(f"  BANNED in Standard: {c.name!r}")

        if deck_issues:
            decks_with_issues += 1
            if verbose:
                issue_lines.append(f"\n=== {os.path.basename(path)} ===")
                issue_lines.extend(deck_issues)

    print(f"Decks scanned: {decks_scanned}")
    print(f"Decks with issues: {decks_with_issues}")

    if empty_oracles:
        print(f"\nCards with EMPTY oracle text ({len(empty_oracles)} unique):")
        for name, paths in sorted(empty_oracles.items()):
            print(f"  {name!r:50s} in {len(paths)} deck(s): {paths[0]}")

    if unknown_cards:
        print(f"\nUNKNOWN cards (not in card_db, {len(unknown_cards)} unique):")
        for name, paths in sorted(unknown_cards.items()):
            print(f"  {name!r:50s} in {len(paths)} deck(s): {paths[0]}")

    if banned_finds:
        print(f"\nBANNED cards in Standard decks ({len(banned_finds)} unique):")
        for name, paths in sorted(banned_finds.items()):
            for p in paths:
                print(f"  {name!r:40s} in {p}")

    if not (empty_oracles or unknown_cards or banned_finds):
        print("\nNo deck data issues found.")


def main():
    verbose = "--verbose" in sys.argv
    mode = "sb"  # default
    if "--decks" in sys.argv:
        mode = "decks"
    elif "--all" in sys.argv:
        mode = "all"

    if mode in ("decks", "all"):
        print("=" * 60)
        print("DECK DATA AUDIT")
        print("=" * 60)
        audit_decks(verbose=verbose)
        print()

    if mode == "decks":
        return

    print("=" * 60)
    print("SB PLAN AUDIT")
    print("=" * 60)
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
