"""apl/izzet_lesson_standard_match.py -- Izzet Lesson match APL.

Multi-inherits MatchAPL + IzzetLessonAPL so the goldfish turn loop
(ControlAPL with categorized disruption) runs unchanged in match
mode. MatchAPL provides declare_attackers / declare_blockers /
respond_to_spell hooks with sensible defaults.
"""
from apl.match_apl import MatchAPL
from apl.izzet_lesson import IzzetLessonAPL


class IzzetLessonStandardMatchAPL(MatchAPL, IzzetLessonAPL):
    ARCHETYPE = "control"
    SB_PLANS = {
        "aggro": (
            ["1 Abrade", "1 Pyroclasm", "1 Slagstorm", "1 Iroh's Demonstration"],
            ["3 Abandon Attachments", "1 Starting Town"],
        ),
        "control": (
            ["2 Annul", "1 Flashfreeze", "1 Negate", "1 Spell Pierce",
             "1 Abhorrent Oculus"],
            ["4 Combustion Technique", "2 It'll Quench Ya!"],
        ),
        "combo": (
            ["3 Soul-Guide Lantern", "2 Annul", "1 Negate", "1 Spell Pierce"],
            ["4 Combustion Technique", "2 It'll Quench Ya!", "1 Agna Qel'a"],
        ),
        "ramp": (
            ["1 Flashfreeze", "1 Negate", "1 Spell Pierce", "2 Quantum Riddler"],
            ["4 Combustion Technique", "1 It'll Quench Ya!"],
        ),
        "tempo": (
            ["1 Abrade", "1 Pyroclasm", "1 Slagstorm", "2 Annul"],
            ["3 Abandon Attachments", "2 It'll Quench Ya!"],
        ),
    }
