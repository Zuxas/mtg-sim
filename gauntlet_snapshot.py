"""
gauntlet_snapshot.py -- read a testing-gauntlet snapshot saved by
mtg-meta-analyzer (Tournament Prep > GAUNTLET, analysis/gauntlet.py).

Schema "mtg-meta-analyzer/gauntlet@1". The parts mtg-sim uses:
  field      {archetype: percent} normalized TESTING weights of the selected
             decks -- the same shape as format_config.get_field()
  entries[]  per archetype: selected, decklist {text, event, event_date, ...}
             (decklist text is "N Card" lines, then "Sideboard", then more)
  content_sha256  hash of the file minus that key; load_snapshot() refuses a
             file edited after it was saved, so a result can be tied to the
             exact field it was run against.

Usage:
    python gauntlet_snapshot.py <snapshot.json>      # print the field
"""
from __future__ import annotations

import hashlib
import json
import sys

SCHEMA = "mtg-meta-analyzer/gauntlet@1"


def _hash(snap: dict) -> str:
    # Must match mtg-meta-analyzer analysis/gauntlet.py _hash().
    body = {k: v for k, v in snap.items() if k != "content_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def load_snapshot(path: str) -> dict:
    """Read a snapshot; raise ValueError on a wrong schema or a hash mismatch."""
    with open(path, encoding="utf-8") as f:
        snap = json.load(f)
    if snap.get("schema") != SCHEMA:
        raise ValueError(f"not a {SCHEMA} file: {snap.get('schema')!r}")
    if snap.get("content_sha256") != _hash(snap):
        raise ValueError("content hash mismatch: the file was edited after it was saved")
    return snap


def field(snap: dict, top_n: int | None = None) -> dict:
    """{archetype: percent}, largest first -- drop-in for get_field().
    Like get_field(), a top_n cut is NOT renormalized (the kept weights sum to
    less than 100); field-weighted drivers divide by the weight they used."""
    items = sorted(snap["field"].items(), key=lambda kv: (-kv[1], kv[0].casefold()))
    return dict(items[:top_n] if top_n else items)


def decklist_text(snap: dict, archetype: str) -> str | None:
    """The representative list for one archetype, or None when it has none."""
    for e in snap["entries"]:
        if e["archetype"].casefold() == archetype.casefold():
            return (e.get("decklist") or {}).get("text")
    return None


def missing_lists(snap: dict) -> list:
    """Selected archetypes with no representative list. Drivers that model
    opponents by archetype clock (gauntlet_any_deck) don't need the list;
    a played-out match from the snapshot alone does."""
    return [e["archetype"] for e in snap["entries"]
            if e["selected"] and not (e.get("decklist") or {}).get("text")]


def load_decks(snap: dict) -> dict:
    """{archetype: (mainboard, sideboard)} Card lists for every selected
    archetype that has a list. Needs the local Scryfall card data."""
    from data.deck import load_deck_from_text
    return {a: load_deck_from_text(t) for a in field(snap)
            if (t := decklist_text(snap, a))}


def describe(snap: dict) -> list:
    """ASCII-only summary lines."""
    w = snap["window"]
    lines = [f"Gauntlet {snap['format']} {w['since']}..{w['until']} "
             f"(field source: {snap['field_source']}, saved {snap.get('created_at')})"]
    for arch, pct in field(snap).items():
        d = None
        for e in snap["entries"]:
            if e["archetype"] == arch:
                d = e.get("decklist")
        prov = f"{d['event']} {d['event_date']}" if d else "NO LIST"
        lines.append(f"  {arch:<30} {pct:>5.1f}%  {prov}")
    return [ln.encode("ascii", "replace").decode() for ln in lines]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[-1].strip())
        sys.exit(2)
    try:
        s = load_snapshot(sys.argv[1])
    except (OSError, ValueError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    print("\n".join(describe(s)))
    for a in missing_lists(s):
        print(f"  WARN: no decklist for {a}")
