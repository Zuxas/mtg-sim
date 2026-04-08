"""apl/jeskai_control.py — Jeskai / Azorius Control APL (Modern)
Teferi + Narset + Solitude + Supreme Verdict.
Kill clock: T5-7 via planeswalker ultimates or Teferi beats.
Models holding up counter mana and sweeping on T4.
"""
from apl.base_apl import BaseAPL
from engine.game_state import GameState

TEFERI   = "Teferi, Time Raveler"
NARSET   = "Narset, Parter of Veils"
SOLITUDE = "Solitude"
VERDICT  = "Supreme Verdict"
ORIM     = "Orim's Chant"
FON      = "Force of Negation"
COUNTER  = "Counterspell"
PRISMATIC= "Prismatic Ending"
ISOCHRON = "Isochron Scepter"
SPELL_SNARE = "Spell Snare"

class JeskaiControlAPL(BaseAPL):
    name = "Jeskai Control"
    win_condition_damage = 20
    max_turns = 16

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands   = sum(1 for c in hand if c.is_land())
        has_pws = any(c.name in {TEFERI, NARSET} for c in hand)
        has_ctr = any(c.name in {FON, COUNTER, SOLITUDE, ORIM} for c in hand)
        if lands == 0: return False
        if lands >= 3 and (has_pws or has_ctr): return True
        if lands >= 2 and has_pws and has_ctr: return True
        return len(hand) <= 5 or mulligans >= 2

    def bottom(self, hand, n):
        threats = [c for c in hand if not c.is_land() and c.name not in {TEFERI, NARSET, SOLITUDE}]
        return threats[-n:][:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        mana = gs.mana_pool.available()
        # Early sweeper if we're behind
        creatures_on_bf = [c for c in gs.battlefield() if not c.is_land()]
        if gs.turn >= 4:
            for card in list(gs.hand()):
                if card.name == VERDICT and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    gs._log("  Supreme Verdict → board wipe")
                    break
        # Deploy Teferi / Narset
        for name in (TEFERI, NARSET, ISOCHRON):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    # Teferi: bounce their stuff, deal 1 per turn
                    if card.name == TEFERI:
                        gs.damage_dealt += gs.turn  # models ticking up
                    break
        # Solitude to remove threats
        for card in list(gs.hand()):
            if card.name == SOLITUDE and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
        # Removal
        for card in list(gs.hand()):
            if card.name == PRISMATIC and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
