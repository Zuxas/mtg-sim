"""apl/roaming_elementals_standard_match.py -- Roaming Elementals match APL (Standard)"""
from apl.match_apl import MatchAPL
from apl.roaming_elementals_standard import RoamingElementalsAPL


class RoamingElementalsStandardMatchAPL(MatchAPL, RoamingElementalsAPL):
    ARCHETYPE = "tempo"
    SB_PLANS = {
        "aggro": (
            ["2 Beza, the Bounding Spring", "1 Broadside Barrage"],
            ["2 Disdainful Stroke", "1 Bounce Off"],
        ),
        "control": (
            ["2 Disdainful Stroke", "1 Deceit"],
            ["2 Beza, the Bounding Spring", "1 Broadside Barrage"],
        ),
        "combo": (
            ["2 Disdainful Stroke", "1 Bounce Off"],
            ["2 Beza, the Bounding Spring", "1 Broadside Barrage"],
        ),
        "ramp": (
            ["2 Disdainful Stroke", "1 Deceit"],
            ["2 Beza, the Bounding Spring", "1 Bounce Off"],
        ),
        "tempo": (
            ["1 Broadside Barrage", "1 Bounce Off"],
            ["2 Disdainful Stroke", "1 Beza, the Bounding Spring"],
        ),
    }
