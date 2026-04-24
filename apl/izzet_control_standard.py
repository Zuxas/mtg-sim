"""Izzet Control (Standard) — GenericAPL shim.

Stub-quality APL for gauntlet coverage against post-Strixhaven brews
that lack tournament matchup data. Decklist scraped from placement-1
finish on 2026-04-15 (Aedand). Uses GenericAPL's role='control'
heuristic: aggressive mull to find interaction + card-draw curve.

To upgrade: hand-tune sequencing for Stock Up / Stormchaser's Talent
synergy, add match-aware removal targeting, write a dedicated
MatchAPL. Skipped for now because Izzet Lessons is the locked deck;
this exists only to play the OPPONENT side of the narrow gauntlet.
"""
from __future__ import annotations
from apl.generic_apl import GenericAPL


class IzzetControlAPL(GenericAPL):
    name = "Izzet Control"

    def __init__(self):
        super().__init__(deck_name="Izzet Control", role="control")
