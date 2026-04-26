"""Yawgmoth (Modern) — GenericAPL shim.

Stub-quality APL for gauntlet coverage. Modern Yawgmoth is the
Yawgmoth-Thran-Physician + Persist creatures combo (Young Wolf,
Geralf's Messenger, Hapatra, Grist) with Collected Company /
Chord of Calling for finding combo pieces. MatchAPL
(apl/yawgmoth_match.py) existed but no goldfish APL was registered.

Role 'combo' fits Yawgmoth's persist-loop plan but GenericAPL
doesn't model the Yawgmoth combo (sac persist creature -> draw +
ping -> persist creature returns -> repeat). Goldfish under-
represents the deck's real speed.

To upgrade: hand-tune the Yawgmoth combo loop with explicit
sac-and-recurse logic. Out of scope tonight.

Stage A of 2026-04-26 no-APL triage.
"""
from __future__ import annotations
from apl.generic_apl import GenericAPL


class YawgmothAPL(GenericAPL):
    name = "Yawgmoth"

    def __init__(self):
        super().__init__(deck_name="Yawgmoth", role="combo")
