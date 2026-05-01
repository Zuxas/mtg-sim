#!/usr/bin/env python3
"""
Build data/priority_queue/meta_share_by_deck.json from the meta-analyzer DB.

Queries Standard events within a configurable date window, aggregates unique
decks per archetype, slugifies archetype names to match the local
`decks/*_standard.txt` filenames, and writes shares keyed by that slug.

Only archetypes that have a matching local decklist are kept — the share
is meaningful only for decks the sim can actually run against.

Usage:
    python scripts/build_meta_shares.py                   # default: last 90 days
    python scripts/build_meta_shares.py --days 180
    python scripts/build_meta_shares.py --from 2025-09-01 --to 2025-10-31
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Set

REPO_ROOT = Path(__file__).resolve().parent.parent
os.chdir(REPO_ROOT)

META_DB_PATH = Path(os.environ.get(
    "MTG_META_DB",
    REPO_ROOT.parent / "mtg-meta-analyzer" / "data" / "mtg_meta.db"
))
OUTPUT_PATH = Path("data/priority_queue/meta_share_by_deck.json")
DECKS_DIR = Path("decks")


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def local_standard_deck_slugs() -> Set[str]:
    slugs: Set[str] = set()
    for path in DECKS_DIR.glob("*_standard.txt"):
        stem = path.stem.lower()
        if stem.endswith("_standard"):
            stem = stem[:-9]
        slugs.add(stem)
    return slugs


def slugify_archetype(name: str) -> str:
    """Match the mtg_meta archetype names to the local decklist slug convention."""
    if not name:
        return ""
    lowered = name.lower().strip()
    return (
        lowered
        .replace("/", "_")
        .replace("-", "_")
        .replace("'", "")
        .replace(",", "")
        .replace(".", "")
        .replace(" ", "_")
    )


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=90,
                    help="Window in days back from today (ignored if --from/--to set)")
    ap.add_argument("--from", dest="from_date", help="YYYY-MM-DD window start")
    ap.add_argument("--to", dest="to_date", help="YYYY-MM-DD window end")
    ap.add_argument("--db", default=str(META_DB_PATH), help="Path to mtg_meta.db")
    ap.add_argument("--output", default=str(OUTPUT_PATH), help="Output JSON path")
    ap.add_argument("--min-decks", type=int, default=5,
                    help="Drop archetypes with fewer than this many decks")
    return ap.parse_args()


def resolve_window(args: argparse.Namespace) -> tuple[str, str]:
    """Return (iso_from, iso_to). DB stores dates as DD/MM/YY, so we return
    sort-friendly YY-MM-DD strings for comparison via substr() slicing."""
    if args.from_date and args.to_date:
        iso_from = args.from_date
        iso_to = args.to_date
    else:
        today = date.today()
        start = today - timedelta(days=args.days)
        iso_from = start.strftime("%Y-%m-%d")
        iso_to = today.strftime("%Y-%m-%d")
    yy_from = iso_from[2:4] + "-" + iso_from[5:7] + "-" + iso_from[8:10]
    yy_to   = iso_to[2:4]   + "-" + iso_to[5:7]   + "-" + iso_to[8:10]
    return yy_from, yy_to, iso_from, iso_to  # type: ignore[return-value]


def main() -> None:
    args = parse_args()
    yy_from, yy_to, iso_from, iso_to = resolve_window(args)

    local_slugs = local_standard_deck_slugs()
    if not local_slugs:
        print(f"No *_standard.txt files in {DECKS_DIR}, nothing to match.")
        sys.exit(1)

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"DB not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    cur.execute(
        """
        SELECT d.archetype, COUNT(DISTINCT d.id) AS n_decks
        FROM decks d
        JOIN events e ON d.event_id = e.id
        WHERE LOWER(e.format) = 'standard'
          AND substr(e.date,7,2)||'-'||substr(e.date,4,2)||'-'||substr(e.date,1,2)
              BETWEEN ? AND ?
        GROUP BY d.archetype
        HAVING n_decks >= ?
        ORDER BY n_decks DESC
        """,
        (yy_from, yy_to, args.min_decks),
    )

    archetype_counts: Dict[str, int] = {}
    for archetype, n_decks in cur.fetchall():
        if not archetype:
            continue
        slug = slugify_archetype(archetype)
        if slug in local_slugs:
            archetype_counts[slug] = archetype_counts.get(slug, 0) + int(n_decks)

    total = sum(archetype_counts.values())
    if total == 0:
        print("No matched archetypes in window. "
              f"Window: {iso_from}..{iso_to}  local slugs: {len(local_slugs)}")
        sys.exit(1)

    shares = {slug: count / total for slug, count in archetype_counts.items()}

    output_path = Path(args.output)
    ensure_parent_dir(output_path)
    output_path.write_text(
        json.dumps(shares, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(f"Window: {iso_from} .. {iso_to}  ({args.days} days default if unset)")
    print(f"Matched {len(shares)} archetypes / {total} decks "
          f"out of {len(local_slugs)} local deck files")
    print()
    print(f"{'Share':>7}  {'Decks':>6}  Slug")
    for slug, share in sorted(shares.items(), key=lambda kv: -kv[1]):
        print(f"{share:>6.1%}  {archetype_counts[slug]:>6}  {slug}")
    print(f"\nWrote {output_path}")


if __name__ == "__main__":
    main()
