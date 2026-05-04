"""apl/dimir_excruciator_standard_match.py -- Dimir Excruciator match APL (Standard)

Victor Santos Esquici 3.1% PT SOS field. Control shell using Excruciator of Sins
as a recursive threat. Proxy GolgariMidrangeStandardMatchAPL game plan (midrange/control).
"""
from apl.match_apl import MatchAPL
from apl.generic_apl import GenericAPL


class DimirExcruciatorStandardMatchAPL(MatchAPL, GenericAPL):
    ARCHETYPE = "control"
    SB_PLANS = {
        "aggro": (
            ["3 Oildeep Gearhulk", "2 Qarsi Revenant"],
            ["2 Flashfreeze", "3 counterspells"],
        ),
        "control": (
            ["2 Flashfreeze", "3 Oildeep Gearhulk"],
            ["3 Qarsi Revenant", "2 removal"],
        ),
        "combo": (
            ["2 Flashfreeze", "3 Oildeep Gearhulk", "2 Qarsi Revenant"],
            ["3 slow threats", "4 creatures"],
        ),
        "ramp": (
            ["2 Flashfreeze", "3 Oildeep Gearhulk"],
            ["2 Qarsi Revenant", "3 creatures"],
        ),
        "tempo": (
            ["3 Oildeep Gearhulk", "2 Qarsi Revenant"],
            ["2 Flashfreeze", "3 slow spells"],
        ),
    }

    def __init__(self):
        GenericAPL.__init__(self, deck_name="Dimir Excruciator", role="control")
