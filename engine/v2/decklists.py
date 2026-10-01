"""Load a real repository deck list for engine v2 (main deck only; sideboards are a later
milestone). Every card must resolve exactly and be explicitly supported -- no substitution."""
from __future__ import annotations

import os
import re

from engine.v2.cards import ROOT, validate_deck

_LINE = re.compile(r"^\s*(\d+)\s+(.+?)\s*$")


def main_deck(name: str) -> list:
    """Card names of decks/<name>.txt's main deck (or of the deck file `name` when it is a path to an
    existing .txt file), in file order, expanded by quantity."""
    path = name if name.endswith(".txt") and os.path.isfile(name) else os.path.join(ROOT, "decks", f"{name}.txt")
    out = []
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if not s or s.startswith("//"):
            continue
        if s.lower().startswith("sideboard"):
            break
        m = _LINE.match(s)
        if not m:
            raise ValueError(f"unparseable deck line in {path}: {line!r}")
        out += [m.group(2)] * int(m.group(1))
    validate_deck(out)                                  # UnknownCardError / UnsupportedCardError
    return out
