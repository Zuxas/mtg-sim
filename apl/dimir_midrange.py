"""apl/dimir_midrange.py — Dimir Midrange APL (Standard)
Thoughtseize effects + Fatal Push + value creatures.
Kill clock: T4-5 grindy beatdown.
"""
from apl.base_apl import BaseAPL
from engine.game_state import GameState

# Standard Dimir threats/disruption
PSYCHIC  = "Psychic Frog"
OVERLORD = "Overlord of the Balemurk"
BOGGART  = "Boggart Trawler"
PUSH     = "Fatal Push"
THOUGHTSEIZE="Thoughtseize"
INQUISITION="Inquisition of Kozilek"
RAFFINE  = "Raffine, Scheming Seer"
SHEOLDRED= "Sheoldred, the Apocalypse"
PREORDAIN= "Preordain"
CONSIDER = "Consider"

class DimirMidrangeAPL(BaseAPL):
    name = "Dimir Midrange"
    win_condition_damage = 20
    max_turns = 14

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands   = sum(1 for c in hand if c.is_land())
        disrupt = sum(1 for c in hand if c.name in {THOUGHTSEIZE, INQUISITION, PUSH})
        threats = sum(1 for c in hand if c.name in {PSYCHIC, OVERLORD, SHEOLDRED, RAFFINE})
        if lands == 0: return False
        if lands >= 2 and (disrupt + threats >= 2): return True
        return len(hand) <= 5 or mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[3:][:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        for name in (THOUGHTSEIZE, INQUISITION):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    gs._log("  Thoughtseize → stripped best card")
                    break
        for name in (PSYCHIC, BOGGART, RAFFINE, SHEOLDRED, OVERLORD):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        for card in list(gs.hand()):
            if card.name == PUSH and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
        for card in list(gs.hand()):
            if card.name in {PREORDAIN, CONSIDER} and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
