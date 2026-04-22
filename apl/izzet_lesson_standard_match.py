"""apl/izzet_lesson_standard_match.py -- Izzet Lesson match APL.

Multi-inherits MatchAPL + IzzetLessonAPL so the goldfish turn loop
(ControlAPL with categorized disruption) runs unchanged in match
mode. MatchAPL provides declare_attackers / declare_blockers /
respond_to_spell hooks with sensible defaults.
"""
from apl.match_apl import MatchAPL
from apl.izzet_lesson import IzzetLessonAPL


class IzzetLessonStandardMatchAPL(MatchAPL, IzzetLessonAPL):
    pass
