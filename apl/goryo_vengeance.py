"""apl/goryo_vengeance.py — Goryo's Vengeance / Esper Vengeance APL (Modern)
T2 Goryo's Vengeance → Atraxa/Griselbrand → draw 7-14 → win.
Combo deck: modeled via kill-turn distribution in format_config.
This APL handles the fair backup plan (Psychic Frog beatdown).
"""
from apl.base_apl import BaseAPL
from engine.game_state import GameState

GORYO      = "Goryo's Vengeance"
ATRAXA     = "Atraxa, Grand Unifier"
GRISELBRAND= "Griselbrand"
PSYCHIC    = "Psychic Frog"
QUANTUM    = "Quantum Riddler"
MENDING    = "Faithful Mending"
SOLITUDE   = "Solitude"
EPHEMERATE = "Ephemerate"
FON        = "Force of Negation"
THOUGHTSEIZE="Thoughtseize"
PRISMATIC  = "Prismatic Ending"
TAINTED    = "Tainted Indulgence"

FATTIES = {ATRAXA, GRISELBRAND}

class GoryoVengeanceAPL(BaseAPL):
    name = "Goryo's Vengeance"
    win_condition_damage = 20
    max_turns = 10

    def __init__(self):
        self._fatty_in_gy = False

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        has_goryo = any(c.name == GORYO for c in hand)
        has_fatty = any(c.name in FATTIES for c in hand)
        has_looting = any(c.name in {MENDING, TAINTED} for c in hand)
        if lands == 0: return False
        # Ideal: Goryo + fatty OR Goryo + looting
        if has_goryo and (has_fatty or has_looting) and lands >= 2: return True
        if lands >= 2 and any(c.name in {PSYCHIC, QUANTUM} for c in hand): return True
        return len(hand) <= 5 or mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        extra = lands[3:]
        return extra[:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        # Looting to find / discard fatty
        for card in list(gs.hand()):
            if card.name in {MENDING, TAINTED} and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                has_fatty = any(c.name in FATTIES for c in gs.hand())
                if has_fatty:
                    self._fatty_in_gy = True
                    gs._log("  Looting → fatty in graveyard")
                break
        # Goryo's Vengeance if fatty in GY
        if self._fatty_in_gy:
            for card in list(gs.hand()):
                if card.name == GORYO and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    token = gs._make_token("Atraxa, Grand Unifier", "7", "7", "Creature")
                    token.summoning_sickness = False
                    gs._log("  Goryo's Vengeance → Atraxa in play")
                    break
        # Backup fair plan: Psychic Frog beatdown
        for name in (THOUGHTSEIZE, PSYCHIC, QUANTUM, SOLITUDE):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        for card in list(gs.hand()):
            if card.name == PRISMATIC and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
