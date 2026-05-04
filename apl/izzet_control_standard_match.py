"""apl/izzet_control_standard_match.py -- Izzet Control match APL (Standard)"""
from apl.match_apl import MatchAPL
from apl.izzet_control_standard import IzzetControlAPL


class IzzetControlStandardMatchAPL(MatchAPL, IzzetControlAPL):
    ARCHETYPE = "control"
    SB_PLANS = {
        "aggro": (
            ["1 Broadside Barrage", "1 Fire Magic", "1 Hearth Elemental"],
            ["2 Annul", "1 Ral, Crackling Wit"],
        ),
        "control": (
            ["2 Ral, Crackling Wit", "2 Annul"],
            ["1 Broadside Barrage", "1 Fire Magic", "2 Essence Scatter"],
        ),
        "combo": (
            ["2 Annul", "1 Broadside Barrage"],
            ["2 Ral, Crackling Wit", "1 Hearth Elemental"],
        ),
        "ramp": (
            ["2 Annul", "2 Ral, Crackling Wit"],
            ["1 Broadside Barrage", "1 Hearth Elemental", "2 Essence Scatter"],
        ),
        "tempo": (
            ["2 Annul", "1 Fire Magic"],
            ["2 Ral, Crackling Wit", "1 Hearth Elemental"],
        ),
    }
