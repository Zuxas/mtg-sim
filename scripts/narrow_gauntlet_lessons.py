#!/usr/bin/env python3
"""Narrow gauntlet — Izzet Lessons vs the 5 post-Strixhaven brews.

These 5 archetypes are ~24% of the current Standard meta but have
no tournament matchup_matrix data yet (too new). The real-world DB
answered Izzet Lessons as the deck pick based on the 75% of meta
covered by 6,338 tournament matches; this sim gauntlet covers the
remaining 25%.

n=25000 per matchup is the tradeoff: enough to produce stable WRs
for a diagnostic read, short enough to finish in 1-2 hours wall-time
so results are available next morning rather than 8+ hours out.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Force UTF-8 stdout — parallel_launcher prints box-drawing chars
# that break cp1252 when stdout is redirected to a file on Windows.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from parallel_launcher import launch_all

# 5 post-Strixhaven brews, meta shares from the 2026-04-23 regeneration.
# Omits Simic Rhythm and the tournament-data-covered decks on purpose
# — those are questions the real-world matchup_matrix already answered.
FIELD = {
    "Superior Doomsday":   7.3,
    "Izzet Control":       5.0,
    "Roaming Elementals":  4.5,
    "Azorius Aggro":       3.6,
    "Mono Green Aggro":    3.6,
}

if __name__ == "__main__":
    launch_all(
        our_deck="Izzet Lessons",
        format_name="standard",
        field=FIELD,
        n=25000,
        cores=20,
        seed=42,
    )
