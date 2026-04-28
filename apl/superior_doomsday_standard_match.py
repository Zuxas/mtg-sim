"""apl/superior_doomsday_standard_match.py -- Superior Doomsday match APL.

Multi-inherits MatchAPL + SuperiorDoomsdayAPL (ControlAPL shell).
"""
from apl.match_apl import MatchAPL
from apl.superior_doomsday_standard import SuperiorDoomsdayAPL


class SuperiorDoomsdayStandardMatchAPL(MatchAPL, SuperiorDoomsdayAPL):
    ARCHETYPE = "control"
    SB_PLANS = {
        "aggro": (
            ["2 Pyroclasm", "2 Get Lost", "2 Tishana's Tidebinder"],
            ["2 Intimidation Tactics", "2 Insatiable Avarice",
             "2 Winternight Stories"],
        ),
        "control": (
            ["2 Duress", "2 Spell Pierce", "2 Exorcise"],
            ["2 Deadly Cover-Up", "2 Intimidation Tactics", "2 Requiting Hex"],
        ),
        "combo": (
            ["3 Soul-Guide Lantern", "2 Duress", "2 Spell Pierce"],
            ["2 Intimidation Tactics", "3 Requiting Hex", "2 Deadly Cover-Up"],
        ),
        "ramp": (
            ["2 Duress", "2 Spell Pierce", "2 Exorcise"],
            ["2 Intimidation Tactics", "2 Deadly Cover-Up", "2 Requiting Hex"],
        ),
        "tempo": (
            ["2 Spell Pierce", "2 Pyroclasm", "2 Tishana's Tidebinder"],
            ["2 Deadly Cover-Up", "2 Intimidation Tactics", "2 Winternight Stories"],
        ),
    }
