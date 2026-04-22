"""apl/izzet_lesson_standard_match.py -- Izzet Lesson match APL.

Match-style APL wrapper around the IzzetLessonAPL goldfish logic.
MatchAPL extends the goldfish base with stop-conditions keyed to
opponent board state (deal lethal if attackers + burn in hand can
close the game; hold up removal when opp has a tapped-in lethal
threat next turn; etc.).

For now this is a minimal wrapper — inherits the goldfish play
patterns and adds match-aware stop conditions via MatchAPL.
"""
from apl.match_apl import MatchAPL
from apl.control_base import ControlAPL
from apl.izzet_lesson import (
    IzzetLessonAPL,
    GRAN_GRAN, FIREBENDING, STORMCHASER, ARTIST,
    ACCUMULATE, MONUMENT,
    COMBUSTION, ABANDON, BOOMERANG,
    IROH, QUENCH,
)


class IzzetLessonStandardMatchAPL(MatchAPL):
    """Match APL. Inherits MatchAPL's stop-conditions and sideboard
    wiring; delegates decision logic to the same categorized
    ControlAPL split via the same class attributes as the goldfish."""

    name = "Izzet Lesson"
    win_condition_damage = 20
    max_turns = 15

    # Same card declarations as the goldfish APL
    HAND_ATTACK = ()
    REMOVAL = (COMBUSTION, ABANDON, BOOMERANG)
    COUNTERS = ()
    WIPES = ()
    THREATS = (GRAN_GRAN, FIREBENDING, STORMCHASER, ARTIST,
                MONUMENT, QUENCH, IROH)
    VALUE_SPELLS = (ACCUMULATE,)

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in self.THREATS)
        removal = sum(1 for c in hand if c.name in self.REMOVAL)
        if lands < 2 or lands > 5:
            return False
        if threats + removal >= 2:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        if len(lands) > 4:
            return lands[4:][:n]
        return lands[3:][:n]

    def main_phase(self, gs):
        """Delegate to the ControlAPL turn loop via composition —
        reuse the goldfish's categorized play pattern."""
        IzzetLessonAPL.main_phase(self, gs)

    def main_phase2(self, gs):
        IzzetLessonAPL.main_phase2(self, gs)
