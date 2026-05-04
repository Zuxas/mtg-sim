"""apl/superior_doomsday_standard_match.py -- Superior Doomsday match APL (Standard)

Esper combo-control. Wins via Doomsday pile or Raffine beatdown.
"""
from apl.match_apl import MatchAPL
from apl.superior_doomsday_standard import SuperiorDoomsdayAPL


class SuperiorDoomsdayStandardMatchAPL(MatchAPL, SuperiorDoomsdayAPL):
    ARCHETYPE = "control"
    SB_PLANS = {
        "aggro": (
            ["2 Pyroclasm", "2 Exorcise", "2 Get Lost"],
            ["2 Duress", "2 Spell Pierce", "2 Tishana's Tidebinder"],
        ),
        "control": (
            ["2 Duress", "2 Spell Pierce", "2 Tishana's Tidebinder"],
            ["2 Pyroclasm", "2 Exorcise", "2 Get Lost"],
        ),
        "combo": (
            ["2 Duress", "3 Soul-Guide Lantern", "2 Tishana's Tidebinder"],
            ["2 Pyroclasm", "2 Exorcise", "1 Get Lost"],
        ),
        "ramp": (
            ["2 Duress", "2 Spell Pierce"],
            ["2 Exorcise", "2 Pyroclasm"],
        ),
        "tempo": (
            ["2 Get Lost", "2 Exorcise"],
            ["2 Duress", "2 Spell Pierce"],
        ),
    }
