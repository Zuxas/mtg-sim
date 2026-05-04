"""apl/mono_green_aggro_standard_match.py -- Mono Green Aggro match APL (Standard)"""
from apl.match_apl import MatchAPL
from apl.mono_green_aggro_standard import MonoGreenAggroAPL


class MonoGreenAggroStandardMatchAPL(MatchAPL, MonoGreenAggroAPL):
    ARCHETYPE = "aggro"
    SB_PLANS = {
        "aggro": (
            ["4 Mossborn Hydra"],
            ["2 Eumidian Terrabotanist", "2 Meltstrider's Resolve"],
        ),
        "control": (
            ["4 Mossborn Hydra", "2 Eumidian Terrabotanist"],
            ["2 Meltstrider's Resolve", "4 smaller threats"],
        ),
        "combo": (
            ["4 Mossborn Hydra", "2 Meltstrider's Resolve"],
            ["2 Eumidian Terrabotanist", "4 removal"],
        ),
        "ramp": (
            ["4 Mossborn Hydra"],
            ["2 Eumidian Terrabotanist", "2 Meltstrider's Resolve"],
        ),
        "tempo": (
            ["2 Meltstrider's Resolve", "4 Mossborn Hydra"],
            ["2 Eumidian Terrabotanist", "4 slow threats"],
        ),
    }
