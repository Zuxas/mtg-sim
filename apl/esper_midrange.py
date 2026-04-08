"""apl/esper_midrange.py — Esper Midrange APL (Modern)
Phelia + Thoughtseize + Fatal Push + Solitude. Grindy value/disruption.
Kill clock: T4-6 via creature beats.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState

PHELIA      = "Phelia, Exuberant Shepherd"
FLICKERWISP = "Flickerwisp"
THOUGHTSEIZE= "Thoughtseize"
INQUISITION = "Inquisition of Kozilek"
FATAL_PUSH  = "Fatal Push"
SOLITUDE    = "Solitude"
OVERLORD    = "Overlord of the Balemurk"
QUANTUM     = "Quantum Riddler"
EMPEROR     = "Emperor of Bones"
EPHEMERATE  = "Ephemerate"
TEFERI      = "Teferi, Time Raveler"

class EsperMidrangeAPL(SBPlanMixin, BaseAPL):
    name = "Esper Midrange"
    win_condition_damage = 20
    max_turns = 14

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands   = sum(1 for c in hand if c.is_land())
        disrupt = sum(1 for c in hand if c.name in {THOUGHTSEIZE, INQUISITION, FATAL_PUSH})
        threats = sum(1 for c in hand if c.name in {PHELIA, OVERLORD, QUANTUM, SOLITUDE})
        if lands == 0: return False
        if lands >= 2 and (disrupt >= 1 or threats >= 1): return True
        return len(hand) <= 5 or mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[3:][:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        # Disrupt first, then deploy threats
        for name in (THOUGHTSEIZE, INQUISITION):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    gs._log("  Thoughtseize → stripped their best card")
                    break
        for name in (PHELIA, SOLITUDE, QUANTUM, OVERLORD, EMPEROR, FLICKERWISP, TEFERI):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        for card in list(gs.hand()):
            if card.name == FATAL_PUSH and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
