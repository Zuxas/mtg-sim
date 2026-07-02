"""scripts/response_coverage_sweep.py -- Stage 2 coverage sweep (07-01 G3).

Runs the oracle-driven response classifier (engine/response_capability.py)
over every instant / flash card in every decklist under decks/ and emits
data/response_coverage.csv with one row per (card, deck):

  status:
    DERIVED             -- classifier derived >=1 response capability
    WHITELIST_FALLBACK  -- no derivation, but the card has a whitelist entry
                           (COUNTER_VALIDITY / any MATCH_REMOVAL / MATCH_BOUNCE)
                           so the legacy tables still model it
    INERT               -- no response-looking oracle text; correctly not an
                           answer (draw/pump/ramp instants)
    UNHANDLED           -- response-looking text the v1 grammar declined and
                           NO whitelist entry covers -- the honest tail;
                           listed so it is never silently wrong

Usage:  python scripts/response_coverage_sweep.py
Deterministic: rows sorted by (deck, card); no RNG, no game state.
"""
import csv
import importlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.response_capability import classify, removal_spec_from  # noqa: E402
from engine.card_db import CardDB  # noqa: E402
from engine.counter_resolver import COUNTER_VALIDITY  # noqa: E402
from apl.match_apl import MatchAPL  # noqa: E402

_RESPONSEISH = re.compile(
    r"counter target|destroy target|exile target"
    r"|deals\b[^.]*\bdamage\b[^.]*\bto (?:any target|target)"
    r"|return target\b[^.]*\bhand", re.I)


def _whitelist_union():
    names = set(COUNTER_VALIDITY) | set(MatchAPL.MATCH_REMOVAL)
    from apl import APL_REGISTRY
    for key, (mod_path, cls_name, _stub) in sorted(APL_REGISTRY.items()):
        try:
            cls = getattr(importlib.import_module(mod_path), cls_name)
        except Exception:
            continue
        for attr in ("MATCH_REMOVAL", "MATCH_BOUNCE"):
            v = getattr(cls, attr, None)
            if isinstance(v, dict):
                names |= set(v)
            elif isinstance(v, (set, frozenset, list, tuple)):
                names |= set(v)
    return names


def _deck_card_names(path: Path):
    """Parse 'N Card Name' lines (main + sideboard); tolerant of headers."""
    names = set()
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "//")):
            continue
        m = re.match(r"^(?:SB[: ]\s*)?(\d+)x?\s+(.+)$", line)
        if m:
            names.add(m.group(2).strip())
    return names


def main():
    db = CardDB()
    whitelist = _whitelist_union()
    rows = []
    deck_files = sorted((ROOT / "decks").glob("*.txt"))
    for deck_path in deck_files:
        deck = deck_path.name
        for name in sorted(_deck_card_names(deck_path)):
            entry = db.get(name)
            if entry is None:
                continue
            r = classify(name)
            if not r.timing:
                continue   # not castable at instant speed -- out of sweep
            oracle = db.oracle_text(name)
            responseish = bool(_RESPONSEISH.search(oracle or ""))
            if r.caps:
                status = "DERIVED"
            elif name in whitelist and (responseish or r.guarded):
                status = "WHITELIST_FALLBACK"
            elif responseish or r.unhandled:
                status = "UNHANDLED"
            else:
                status = "INERT"
            spec = removal_spec_from(r.caps)
            rows.append({
                "card": r.name, "deck": deck, "timing": r.timing,
                "status": status,
                "kinds": ";".join(c.kind for c in r.caps),
                "cost": spec[0] if spec else (r.caps[0].cost if r.caps else ""),
                "max_tgh": (spec[1] if spec and spec[1] is not None else ""),
                "detail": ";".join(r.guarded + r.unhandled)[:120],
            })

    out = ROOT / "data" / "response_coverage.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["card", "deck", "timing", "status",
                                          "kinds", "cost", "max_tgh", "detail"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["deck"], r["card"])))

    total = len(rows)
    uniq = {}
    for r in rows:
        uniq.setdefault(r["card"], r["status"])
    by = {}
    for s in uniq.values():
        by[s] = by.get(s, 0) + 1
    u_total = len(uniq)
    print(f"decks swept: {len(deck_files)} | instant/flash rows: {total} "
          f"| unique instant/flash cards: {u_total}")
    for s in ("DERIVED", "WHITELIST_FALLBACK", "INERT", "UNHANDLED"):
        n = by.get(s, 0)
        print(f"  {s:18s} {n:4d}  ({100.0 * n / u_total:.1f}% of unique)")
    acc = u_total - by.get("UNHANDLED", 0)
    print(f"  accounted (never silently wrong): {acc}/{u_total} "
          f"({100.0 * acc / u_total:.1f}%)")
    print(f"wrote {out}")
    print("UNHANDLED tail (unique):")
    for card, s in sorted(uniq.items()):
        if s == "UNHANDLED":
            print(f"  - {card}")


if __name__ == "__main__":
    main()
