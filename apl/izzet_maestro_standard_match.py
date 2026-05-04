"""apl/izzet_maestro_standard_match.py -- Izzet Maestro match APL (Standard / PT SOS 2026)

PT SOS performance: 30.6% FWR (worst in field). Included for gauntlet completeness.
"""
from apl.match_apl import MatchAPL
from apl.izzet_maestro_standard import IzzetMaestroAPL


class IzzetMaestroStandardMatchAPL(MatchAPL, IzzetMaestroAPL):
    ARCHETYPE = "tempo"
    SB_PLANS = {
        "aggro": (
            ["3 Abrade", "2 Slagstorm"],
            ["3 Annul", "2 Bounce Off"],
        ),
        "control": (
            ["3 Annul", "2 Ral, Crackling Wit"],
            ["3 Abrade", "2 Fire Magic"],
        ),
        "combo": (
            ["3 Annul", "2 Soul-Guide Lantern"],
            ["3 Abrade", "2 Fire Magic"],
        ),
        "ramp": (
            ["3 Annul", "3 Abrade"],
            ["3 Bounce Off", "3 Wild Ride"],
        ),
        "tempo": (
            ["3 Abrade", "3 Annul"],
            ["3 Bounce Off", "2 Wild Ride", "1 Opt"],
        ),
    }
