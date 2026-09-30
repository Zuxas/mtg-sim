"""Pinned Comprehensive Rules index (engine v2 gate M0).

Verifies the pinned rules file against data/rules_reference/RULES.json (sha256, size),
then parses it into exact numbered entries: {"103.5": "103.5. Each player ...", "608.3a": ...}.
An entry runs from its numbered line up to the next numbered rule, chapter heading
("8. Multiplayer Rules"), "Glossary" or "Credits" line.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RR = os.path.join(ROOT, "data", "rules_reference")
RULE_LINE = re.compile(r"^(\d{3}(?:\.\d+[a-z]?)?)\.?\s")
CHAPTER_LINE = re.compile(r"^\d\.\s+\S")


class RulesBaselineError(RuntimeError):
    pass


def rules_meta() -> dict:
    with open(os.path.join(RR, "RULES.json"), encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def rules_text() -> str:
    meta = rules_meta()
    path = os.path.join(RR, meta["file"])
    if not os.path.exists(path):
        raise RulesBaselineError(f"pinned rules file missing: {path}")
    data = open(path, "rb").read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != meta["sha256"] or len(data) != meta["bytes"]:
        raise RulesBaselineError(f"pinned rules file changed: sha256 {digest} != {meta['sha256']}")
    return data.decode("utf-8")


@lru_cache(maxsize=1)
def entries() -> dict:
    out: dict = {}
    cur = None
    for line in rules_text().split("\n"):
        m = RULE_LINE.match(line)
        if m:
            cur = m.group(1)
            out[cur] = line.rstrip()           # body occurrence overwrites the table of contents
            continue
        stripped = line.strip()
        if CHAPTER_LINE.match(line) or stripped in ("Glossary", "Credits"):
            cur = None
            continue
        if cur and stripped:
            out[cur] += "\n" + line.rstrip()
    return out


def entry(rule_id: str) -> str:
    e = entries().get(rule_id)
    if e is None:
        raise KeyError(f"rule {rule_id} not in the pinned Comprehensive Rules")
    return e
