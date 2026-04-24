"""Mono Green Aggro (Standard) — GenericAPL shim.

Stub-quality APL for gauntlet coverage. Decklist scraped from
placement-1 finish on 2026-04-09 (GigaChadSigmaMale). Classic
one-drop curve (Llanowar Elves, Badgermole Cub) into Earthbender
Ascension / Mightform Harmonizer. GenericAPL role='aggro'.

To upgrade: sequence ramp creatures before beaters, model
Earthbender Ascension counter-accumulation, wire Fabled Passage /
Ba Sing Se mana interactions. Skipped for now — shim only plays
the OPPONENT side of the narrow gauntlet against Izzet Lessons.
"""
from __future__ import annotations
from apl.generic_apl import GenericAPL


class MonoGreenAggroAPL(GenericAPL):
    name = "Mono Green Aggro"

    def __init__(self):
        super().__init__(deck_name="Mono Green Aggro", role="aggro")
