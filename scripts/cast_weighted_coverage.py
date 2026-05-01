#!/usr/bin/env python3
"""Cast-weighted handler coverage for a format.

Answers "what % of deck-slots played in recent <format> tournaments
are covered by a registered handler?" — the number that actually
tells you whether the sim is ready for a competitive event, as
opposed to card-count coverage which weights 1-of sideboard picks
the same as 4-of threats.

Usage:
    python scripts/cast_weighted_coverage.py [--format standard] [--days 90] [--top 20]

Output:
    Overall coverage percentage + list of top-N unhandled cards
    ranked by slot-contribution (what would move the needle most).
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import os as _os
DB_PATH = Path(_os.environ.get(
    "MTG_META_DB",
    Path(__file__).resolve().parent.parent.parent / "mtg-meta-analyzer" / "data" / "mtg_meta.db"
))


def parse_ddmmyy(s: str):
    """Parse 'DD/MM/YY' → date. Returns None if malformed."""
    try:
        dd, mm, yy = s.split("/")
        y = int(yy)
        # Two-digit year window: 00-49 → 2000s, 50-99 → 1900s.
        year = 2000 + y if y < 50 else 1900 + y
        return date(year, int(mm), int(dd))
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", default="standard")
    ap.add_argument("--days", type=int, default=90,
                    help="Event recency window (default 90)")
    ap.add_argument("--top", type=int, default=20,
                    help="Top-N unhandled cards to list (default 20)")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)
    sys.path.insert(0, str(repo_root))

    # Live handler registry
    try:
        from engine import card_handlers_verified  # noqa: F401
        from engine.card_effects import ETB_EFFECTS, SPELL_EFFECTS
    except Exception as exc:
        print(f"IMPORT_FAILED: {exc}", file=sys.stderr)
        return 2
    registered = set(ETB_EFFECTS.keys()) | set(SPELL_EFFECTS.keys())

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # Pull recent <format>-legal deck_cards slots.
    rows = cur.execute("""
        SELECT c.name, e.date, dc.quantity, dc.is_sideboard
        FROM deck_cards dc
        JOIN cards c ON c.id = dc.card_id
        JOIN decks d ON d.id = dc.deck_id
        JOIN events e ON e.id = d.event_id
        JOIN card_data cd ON cd.name = c.name
        WHERE LOWER(e.format) = ?
          AND json_extract(cd.legalities, '$.' || ?) = 'legal'
    """, (args.format, args.format)).fetchall()

    cutoff = date.today() - timedelta(days=args.days)
    slot_total = 0
    slot_by_card: Counter = Counter()
    for name, date_str, qty, _sb in rows:
        d = parse_ddmmyy(date_str)
        if d is None or d < cutoff:
            continue
        slot_total += qty
        slot_by_card[name] += qty

    if slot_total == 0:
        print(f"No {args.format} deck-slots found in the last {args.days} days.")
        print(f"(events table dates are DD/MM/YY; format='{args.format}' events inside window: 0)")
        return 0

    covered_slots = sum(q for name, q in slot_by_card.items() if name in registered)
    pct = 100.0 * covered_slots / slot_total

    # Unhandled ranked by slot contribution
    unhandled = [(n, q) for n, q in slot_by_card.most_common() if n not in registered]

    print(f"Format: {args.format}    Window: last {args.days} days    "
          f"Total deck-slots: {slot_total}")
    print(f"Distinct cards played: {len(slot_by_card)}    "
          f"Handlers registered: {len(registered)}")
    print()
    print(f"Cast-weighted coverage: {pct:.2f}%  "
          f"({covered_slots} of {slot_total} slots)")
    print(f"Unhandled cards (by slot contribution):")
    remaining_slots = slot_total - covered_slots
    print(f"  {len(unhandled)} distinct cards accounting for {remaining_slots} slots "
          f"({100*remaining_slots/slot_total:.2f}%)")
    print()
    print(f"Top {min(args.top, len(unhandled))} unhandled by slots:")
    for i, (name, q) in enumerate(unhandled[:args.top], 1):
        print(f"  #{i:2d}  {name:40s}  slots={q:5d}  "
              f"({100*q/slot_total:.2f}% of total)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
