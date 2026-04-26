"""Living End (Modern) — GenericAPL shim.

Stub-quality APL for gauntlet coverage. Modern Living End is the
classic cascade combo: cycling creatures fill GY, cascade trigger
casts Living End to mass-reanimate. MatchAPL
(apl/living_end_match.py) existed but no goldfish APL was registered.

Role 'combo' is the closest GenericAPL fit but isn't a great match
for cascade decks -- GenericAPL doesn't model cascade or the
cycle-discard-into-GY plan. Goldfish numbers will under-represent
Living End's actual speed; treat as floor not ceiling.

To upgrade: hand-tune to recognize cascade triggers + GY-stocking
priority for cycling creatures. Out of scope tonight.

Stage A of 2026-04-26 no-APL triage.
"""
from __future__ import annotations
from apl.generic_apl import GenericAPL


class LivingEndAPL(GenericAPL):
    name = "Living End"

    def __init__(self):
        super().__init__(deck_name="Living End", role="combo")
