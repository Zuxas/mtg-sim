"""apl/izzet_prowess_standard_match.py -- Izzet Prowess match APL.

Multi-inherits MatchAPL (for match-mode hooks) + IzzetProwessAPL (for
the full AggroAPL turn loop with all its card declarations and
helper state). No need to override main_phase/main_phase2 — the
goldfish APL's implementations are inherited directly.
"""
from apl.match_apl import MatchAPL
from apl.izzet_prowess_standard import IzzetProwessAPL


class IzzetProwessStandardMatchAPL(MatchAPL, IzzetProwessAPL):
    ARCHETYPE = "tempo"
    SB_PLANS = {
        "aggro": (
            ["2 Eddymurk Crab", "1 Fire Magic", "1 Slagstorm", "2 Get Out"],
            ["2 Wild Ride", "1 Octopus Form", "1 Boomerang Basics", "2 Bounce Off"],
        ),
        "control": (
            ["2 Spell Pierce", "3 Ral, Crackling Wit"],
            ["2 Bounce Off", "2 Boomerang Basics", "1 Octopus Form"],
        ),
        "combo": (
            ["2 Spell Pierce", "2 Soul-Guide Lantern"],
            ["2 Wild Ride", "1 Octopus Form", "1 Boomerang Basics"],
        ),
        "ramp": (
            ["2 Spell Pierce", "3 Ral, Crackling Wit"],
            ["2 Wild Ride", "2 Bounce Off", "1 Octopus Form"],
        ),
        "tempo": (
            ["2 Spell Pierce", "2 Eddymurk Crab", "2 Get Out"],
            ["2 Wild Ride", "1 Octopus Form", "2 Boomerang Basics", "1 Bounce Off"],
        ),
    }
