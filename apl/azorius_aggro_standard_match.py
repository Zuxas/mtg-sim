"""apl/azorius_aggro_standard_match.py -- Azorius Merfolk match APL."""
from apl.match_apl import MatchAPL
from apl.azorius_aggro_standard import AzoriusAggroAPL


class AzoriusAggroStandardMatchAPL(MatchAPL, AzoriusAggroAPL):
    ARCHETYPE = "aggro"
    # Merfolk tribal with Deepchannel Duelist Lord pump — the plan is
    # to swing every turn regardless of trade math. Lord-buffed 3/3s
    # trading with opp 3/3s still chips through over time.
    ATTACK_ALL_IN = True
    SB_PLANS = {
        "control": (
            ["2 Negate", "2 Spell Pierce", "2 Abrupt Inquiry"],
            ["2 Get Lost", "4 Floodpits Drowner"],
        ),
        "aggro": (
            ["2 Get Lost", "2 Temporary Lockdown", "2 Tishana's Tidebinder"],
            ["4 Silvergill Mentor", "2 Abrupt Inquiry"],
        ),
        "combo": (
            ["3 Soul-Guide Lantern", "2 Negate", "2 Spell Pierce"],
            ["4 Silvergill Mentor", "2 Wanderbrine Trapper", "1 Three Steps Ahead"],
        ),
        "ramp": (
            ["2 Negate", "2 Spell Pierce", "2 Temporary Lockdown"],
            ["2 Get Lost", "4 Silvergill Mentor"],
        ),
        "tempo": (
            ["2 Get Lost", "2 Spell Pierce", "2 Tishana's Tidebinder"],
            ["4 Silvergill Mentor", "2 Abrupt Inquiry"],
        ),
    }
