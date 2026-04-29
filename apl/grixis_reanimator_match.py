"""
apl/grixis_reanimator_match.py — Grixis Reanimator (Modern)

Combo: Unmarked Grave + Persist -> Archon of Cruelty / Abhorrent Oculus.
Key: Archon ETB makes opponent sacrifice a permanent + discard + lose 3 life.
Abhorrent Oculus ETB draws cards and creates flying tokens.

Kill distribution (from format_config.py): T2 15%, T3 45%, T4 30%, T5 10%.
As opponent: routed to ComboKillSampler via format_config 'combo' set.
"""
from apl.match_apl import MatchAPL
from data.card import Tag
from engine.match_state import safe_power

ARCHON = "Archon of Cruelty"
OCULUS = "Abhorrent Oculus"
GRAVE = "Unmarked Grave"
PERSIST = "Persist"
THOUGHTSEIZE = "Thoughtseize"


class GrixisReanimatorMatchAPL(MatchAPL):
    name = "Grixis Reanimator"
    win_condition_damage = 20
    max_turns = 8

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        has_tutor = any(c.name in (GRAVE, THOUGHTSEIZE) for c in hand)
        has_reanimate = any(c.name == PERSIST for c in hand)
        has_target = any(c.name in (ARCHON, OCULUS) for c in hand)
        lands = sum(1 for c in hand if c.is_land())
        return ((has_tutor or has_reanimate) and lands >= 1) or mulligans >= 2

    def bottom(self, hand, n):
        high_cmc = sorted([c for c in hand if not c.is_land()],
                          key=lambda c: -getattr(c, 'cmc', 0))
        lands = [c for c in hand if c.is_land()]
        return (lands[3:] + high_cmc)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        # Thoughtseize opponent if available
        if opponent:
            for c in list(gs.zones.hand):
                if c.name == THOUGHTSEIZE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    if opponent.zones.hand:
                        biggest = max(opponent.zones.hand,
                                      key=lambda x: getattr(x, 'cmc', 0))
                        opponent.zones.hand.remove(biggest)
                        opponent.zones.exile.append(biggest)
                        gs._log(f"  Thoughtseize: take {biggest.name}")
                    break
        self._cast_all_castable(gs)

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent): pass
