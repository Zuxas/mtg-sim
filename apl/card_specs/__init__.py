"""apl/card_specs/ — per-card decision logic shared across APLs.

Where engine/card_handlers_verified.py covers RESOLUTION (what happens
when a card resolves on the stack), card_specs covers DECISION (when an
APL chooses to play it, what targeting to pick, sequencing).

Each spec module exports a `NAME` constant and one or more action
functions returning `bool` ("did I do anything?") for orchestration.

Goldfish-aware: every action accepts `opponent=None` and skips dead
branches when there's no opponent state.

Spec: harness/specs/2026-04-29-card-specs-framework.md
Findings: harness/knowledge/tech/jeskai-blink-card-specs-2026-04-28.md
"""
from . import phlage, ragavan, phelia, ephemerate
from . import quantum_riddler, teferi_time_raveler, consign_to_memory, wrath_of_the_skies
from . import (prismari, silverquill, emeritus_of_conflict, rootha,
               veyran, quandrix, the_dawning_archaic, strixhaven_lessons, muddle)

__all__ = [
    # Tier 1 — Modern core (extracted 2026-04-29 POC)
    "phlage", "ragavan", "phelia", "ephemerate",
    # Tier 2 — Modern shared (extracted 2026-04-29)
    "quantum_riddler", "teferi_time_raveler", "consign_to_memory",
    "wrath_of_the_skies",
    # Tier 3 — Secrets of Strixhaven Standard (extracted 2026-04-29)
    "prismari", "silverquill", "emeritus_of_conflict", "rootha",
    "veyran", "quandrix", "the_dawning_archaic", "strixhaven_lessons", "muddle",
]
