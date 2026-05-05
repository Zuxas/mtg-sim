#!/usr/bin/env python3
"""Check whether a card has a live handler registration.

Usage: python scripts/is_handler_registered.py "<Card Name>"

Exit codes:
    0 — registered in ETB_EFFECTS or SPELL_EFFECTS at import time
    1 — not registered
    2 — import failed (registry state unknown)

Prints "YES" or "NO" to stdout so callers don't have to read exit codes.

This is the authoritative check. Do NOT AST-walk or grep the handler
files — those approaches miss registrations that live outside
card_handlers_verified.py (card_effects.py contributes ~6 cards) and
they've produced duplicate-write bugs in the past (Stormchaser's
Talent triplicate, 2026-04-23). Live import is the only reliable path.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: is_handler_registered.py \"<Card Name>\"", file=sys.stderr)
        return 2
    name = sys.argv[1]

    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)
    sys.path.insert(0, str(repo_root))

    try:
        from engine import card_handlers_verified  # noqa: F401  (side-effect import)
        from engine.card_effects import ETB_EFFECTS, SPELL_EFFECTS
    except Exception as exc:
        print(f"IMPORT_FAILED: {exc}", file=sys.stderr)
        return 2

    registered = name in ETB_EFFECTS or name in SPELL_EFFECTS
    print("YES" if registered else "NO")
    return 0 if registered else 1


if __name__ == "__main__":
    sys.exit(main())
