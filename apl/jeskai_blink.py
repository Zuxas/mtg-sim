"""Jeskai Blink (Modern) — GenericAPL shim.

Stub-quality APL for gauntlet coverage. Modern Jeskai Blink:
Phelia + Phlage + Quantum Riddler + Solitude blink shell with
red splash for Casey Jones / removal. MatchAPL (apl/jeskai_blink_match.py)
existed but no goldfish APL was registered.

NB: this is distinct from the registered 'jeskaicontrol' entry
which points at apl/jeskai_control.py (a different Jeskai shell).
The 'jeskaiblink' key needs its own goldfish APL.

Role 'midrange' fits the Phelia + Solitude tempo plan.

Stage A of 2026-04-26 no-APL triage.
"""
from __future__ import annotations
from apl.generic_apl import GenericAPL


class JeskaiBlinkAPL(GenericAPL):
    name = "Jeskai Blink"

    def __init__(self):
        super().__init__(deck_name="Jeskai Blink", role="midrange")
