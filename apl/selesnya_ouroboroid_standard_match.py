"""apl/selesnya_ouroboroid_standard_match.py -- Selesnya Ouroboroid match APL (Standard)

Matt Nass #2 seed at PT SOS 2026. Ouroboroid engine: self-mill + Scavenging Ooze-style
graveyard payoffs. Wins with Craterhoof Behemoth or Ouroboroid beatdown.
"""
from apl.match_apl import MatchAPL
from apl.selesnya_ouroboroid_standard import SelesnyaOuroboroidAPL


class SelesnyaOuroboroidStandardMatchAPL(MatchAPL, SelesnyaOuroboroidAPL):
    ARCHETYPE = "combo"
    SB_PLANS = {
        "aggro": (
            ["1 Focus Fire", "1 Insidious Fungus", "1 Craterhoof Behemoth"],
            ["2 Ouroboroid", "1 Spider Manifestation"],
        ),
        "control": (
            ["3 Rest in Peace", "1 Craterhoof Behemoth"],
            ["2 Ouroboroid", "1 Insidious Fungus", "1 Focus Fire"],
        ),
        "combo": (
            ["3 Rest in Peace", "1 Insidious Fungus"],
            ["2 Ouroboroid", "1 Focus Fire", "1 Craterhoof Behemoth"],
        ),
        "ramp": (
            ["1 Focus Fire", "3 Rest in Peace"],
            ["2 Ouroboroid", "1 Insidious Fungus", "1 Craterhoof Behemoth"],
        ),
        "tempo": (
            ["1 Focus Fire", "1 Insidious Fungus"],
            ["1 Spider Manifestation", "1 Ouroboroid"],
        ),
    }
