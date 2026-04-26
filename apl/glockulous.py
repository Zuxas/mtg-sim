"""Glockulous (Modern) — GenericAPL shim.

Stub-quality APL for gauntlet coverage. Modern Glockulous is a
Grixis Reanimator variant: Psychic Frog + Faithless Looting +
Persist + Archon of Cruelty. The MatchAPL (apl/glockulous_match.py)
existed but no goldfish APL was registered, so any get_apl("Glockulous")
call returned None.

Role 'midrange' picks GenericAPL's curve heuristic that suits a
GY-fueled deck better than aggro/control defaults.

To upgrade: write a hand-tuned APL that models the Persist/Archon
reanimator line + Psychic Frog discard outlets. Skipped tonight --
this exists so the deck can be sim'd at all.

Stage A of 2026-04-26 no-APL triage.
"""
from __future__ import annotations
from apl.generic_apl import GenericAPL


class GlockulousAPL(GenericAPL):
    name = "Glockulous"

    def __init__(self):
        super().__init__(deck_name="Glockulous", role="midrange")
