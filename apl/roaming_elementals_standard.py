"""Roaming Elementals (Standard) — GenericAPL shim.

Stub-quality APL for gauntlet coverage. Decklist scraped from
placement-1 finish on 2026-03-28 (Edel). Elemental tribal midrange
with Roaming Throne + Ashling + Flamebraider. GenericAPL role='midrange'.

To upgrade: model Roaming Throne's triple-trigger on ETB, wire
Cavern of Souls mana fixing, add match-aware threat-prioritization.
Skipped for now — this shim only plays the OPPONENT side of the
narrow gauntlet against Izzet Lessons.
"""
from __future__ import annotations
from apl.generic_apl import GenericAPL


class RoamingElementalsAPL(GenericAPL):
    name = "Roaming Elementals"

    def __init__(self):
        super().__init__(deck_name="Roaming Elementals", role="midrange")
