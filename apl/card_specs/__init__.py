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
# Secrets of Strixhaven Standard — wave 1
from . import (prismari, silverquill, emeritus_of_conflict, rootha,
               veyran, quandrix, the_dawning_archaic, strixhaven_lessons, muddle)
# Secrets of Strixhaven Standard — wave 2
from . import (lorehold, deekah, zaffai, magma_opus, maelstrom_artisan,
               brazen_borrower, ral_zarek_guest_lecturer)
# Secrets of Strixhaven Standard — wave 3
from . import (plargg_and_nassari, witherbloom, serra_paragon, laelia,
               rionya, mathemagics, jadar, ozolith)
# Standard set coverage — all remaining sets (2026-04-29)
from . import (duskmourn_overlords, duskmourn_spells, duskmourn_creatures,
               lorwyn_eclipsed, edge_of_eternities, avatar_the_last_airbender,
               bloomburrow, foundations, aetherdrift, tarkir_dragonstorm,
               final_fantasy, multi_set_standard, standard_remaining,
               strixhaven_support)

__all__ = [
    # Tier 1 — Modern core
    "phlage", "ragavan", "phelia", "ephemerate",
    # Tier 2 — Modern shared
    "quantum_riddler", "teferi_time_raveler", "consign_to_memory",
    "wrath_of_the_skies",
    # Tier 3 — Secrets of Strixhaven Standard (waves 1-3)
    "prismari", "silverquill", "emeritus_of_conflict", "rootha",
    "veyran", "quandrix", "the_dawning_archaic", "strixhaven_lessons", "muddle",
    "lorehold", "deekah", "zaffai", "magma_opus", "maelstrom_artisan",
    "brazen_borrower", "ral_zarek_guest_lecturer",
    "plargg_and_nassari", "witherbloom", "serra_paragon", "laelia",
    "rionya", "mathemagics", "jadar", "ozolith",
    # Standard set coverage — all remaining sets
    "duskmourn_overlords", "duskmourn_spells", "duskmourn_creatures",
    "lorwyn_eclipsed", "edge_of_eternities", "avatar_the_last_airbender",
    "bloomburrow", "foundations", "aetherdrift", "tarkir_dragonstorm",
    "final_fantasy", "multi_set_standard", "standard_remaining",
    "strixhaven_support",
]
