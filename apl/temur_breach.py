"""Temur Breach / Teg (Modern) — GenericAPL shim.

Stub-quality APL for gauntlet coverage. Modern "Teg" / Temur Breach
is a ritual-storm-style combo deck (Desperate Ritual + Artist's
Talent + cantrips).

Role 'combo' matches the ritual-storm plan but GenericAPL won't
correctly sequence cantrip-into-ritual chains. Numbers will
under-represent the deck's real speed.

To upgrade: hand-tune cantrip-into-ritual sequencing + storm-count
tracking. Out of scope tonight.

Stage A of 2026-04-26 no-APL triage. APL_REGISTRY's 'breach' alias
points here as of 2026-05-14 (formerly routed through
apl/grinding_breach.py whose deck file was a bit-identical copy of
this one; that pair was removed).
"""
from __future__ import annotations
from apl.generic_apl import GenericAPL


class TemurBreachAPL(GenericAPL):
    name = "Temur Breach"

    def __init__(self):
        super().__init__(deck_name="Temur Breach", role="combo")
