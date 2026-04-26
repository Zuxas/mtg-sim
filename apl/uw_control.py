"""UW Control (Modern) — GenericAPL shim.

Stub-quality APL for gauntlet coverage. Modern UW Control runs
a planeswalker pile (Narset, Teferi x2, Jace, Wandering Emperor)
plus Solitude / Subtlety / Wan Shi Tong as interaction. MatchAPL
(apl/uw_control_match.py) existed but no goldfish APL was registered.

Role 'control' triggers GenericAPL's aggressive mull for interaction
+ card draw. Goldfish numbers will be PARTICULARLY bad here --
control decks need real opponent simulation to evaluate, and the
planeswalker side isn't modeled by GenericAPL. Treat as registered-
not-validated.

To upgrade: hand-tune planeswalker activation priority + use the
Stage 3 PLANESWALKER_ABILITIES infrastructure (engine/planeswalkers.py).
Out of scope tonight.

Stage A of 2026-04-26 no-APL triage.
"""
from __future__ import annotations
from apl.generic_apl import GenericAPL


class UWControlAPL(GenericAPL):
    name = "UW Control"

    def __init__(self):
        super().__init__(deck_name="UW Control", role="control")
