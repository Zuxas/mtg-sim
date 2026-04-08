"""apl/esper_blink.py — Esper Blink APL (Modern)
Psychic Frog + Phelia + Force of Negation counter engine.
Kill clock: T4-5. Resilient through disruption.
"""
from apl.base_apl import BaseAPL
from engine.game_state import GameState

PSYCHIC_FROG = "Psychic Frog"
PHELIA       = "Phelia, Exuberant Shepherd"
QUANTUM      = "Quantum Riddler"
OVERLORD     = "Overlord of the Balemurk"
EMPEROR      = "Emperor of Bones"
HYDRO        = "Hydroelectric Specimen"
SUBTLETY     = "Subtlety"
EPHEMERATE   = "Ephemerate"
TEFERI       = "Teferi, Time Raveler"
CONSIGN      = "Consign to Memory"
FATAL_PUSH   = "Fatal Push"
FON          = "Force of Negation"

class EsperBlinkAPL(BaseAPL):
    name = "Esper Blink"
    win_condition_damage = 20
    max_turns = 13

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands   = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in {PSYCHIC_FROG, PHELIA, QUANTUM, HYDRO})
        has_fon = any(c.name in {FON, SUBTLETY, CONSIGN} for c in hand)
        if lands == 0: return False
        if lands >= 2 and (threats >= 1 or has_fon): return True
        return len(hand) <= 5 or mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        extra = lands[3:]
        filler = [c for c in hand if c.name in {FON} and len(extra) < n]
        return (extra + filler)[:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        for name in (PSYCHIC_FROG, PHELIA, HYDRO, QUANTUM, OVERLORD, EMPEROR, SUBTLETY, TEFERI):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        for card in list(gs.hand()):
            if card.name == FATAL_PUSH and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
