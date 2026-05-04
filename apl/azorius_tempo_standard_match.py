"""apl/azorius_tempo_standard_match.py -- Azorius Tempo match APL (Standard / PT SOS 2026)"""
from apl.match_apl import MatchAPL
from apl.azorius_tempo_standard import AzoriusTempoAPL


class AzoriusTempoStandardMatchAPL(MatchAPL, AzoriusTempoAPL):
    ARCHETYPE = "tempo"
    SB_PLANS = {
        "aggro": (
            ["4 Doorkeeper Thrull", "2 Soul-Guide Lantern"],
            ["3 Flashfreeze", "2 No More Lies", "1 Essence Scatter"],
        ),
        "control": (
            ["3 Sheltered by Ghosts", "2 Clarion Conqueror"],
            ["3 Get Lost", "2 Annul"],
        ),
        "combo": (
            ["3 Flashfreeze", "1 Rest in Peace", "2 Soul-Guide Lantern"],
            ["3 Get Lost", "2 Voice of Victory", "1 Opt"],
        ),
        "ramp": (
            ["3 Flashfreeze", "3 Sheltered by Ghosts"],
            ["3 Get Lost", "2 Annul", "1 Opt"],
        ),
        "tempo": (
            ["4 Doorkeeper Thrull", "2 Clarion Conqueror"],
            ["3 Flashfreeze", "2 Essence Scatter", "1 Annul"],
        ),
    }
