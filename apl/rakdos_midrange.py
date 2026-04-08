"""apl/rakdos_midrange.py — Rakdos Midrange APL (Pioneer + Standard)
Thoughtseize + Fable + Sheoldred + Graveyard Trespasser.
Kill clock: T4-5 via grinding value + efficient threats.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState

THOUGHTSEIZE = "Thoughtseize"
FABLE        = "Fable of the Mirror-Breaker"
SHEOLDRED    = "Sheoldred, the Apocalypse"
TRESPASSER   = "Graveyard Trespasser"
BLOODTITHE   = "Bloodtithe Harvester"
PUSH         = "Fatal Push"
DREADBORE    = "Dreadbore"
INVOKE_DESP  = "Invoke Despair"
PREORDAIN    = "Preordain"
RECKONER     = "Reckoner Bankbuster"

class RakdosMidrangeAPL(SBPlanMixin, BaseAPL):
    name = "Rakdos Midrange"
    win_condition_damage = 20
    max_turns = 13

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands   = sum(1 for c in hand if c.is_land())
        disrupt = any(c.name in {THOUGHTSEIZE, PUSH} for c in hand)
        threats = any(c.name in {FABLE, SHEOLDRED, TRESPASSER, BLOODTITHE} for c in hand)
        if lands == 0: return False
        if lands >= 2 and (disrupt or threats): return True
        return len(hand) <= 5 or mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[3:][:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        for card in list(gs.hand()):
            if card.name == THOUGHTSEIZE and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                gs._log("  Thoughtseize → stripped best card")
                break
        for name in (BLOODTITHE, FABLE, TRESPASSER, RECKONER, SHEOLDRED, INVOKE_DESP):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        for card in list(gs.hand()):
            if card.name in {PUSH, DREADBORE} and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
