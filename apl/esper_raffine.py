"""apl/esper_raffine.py -- Esper Raffine APL (Standard)
Midrange value shell anchored by Raffine + Liliana disruption.
Kill clock: T5-6 grindy, wins through card advantage + ward creatures.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState

# Disruption / removal
CUT_DOWN     = "Cut Down"
THROAT       = "Go for the Throat"
LILIANA      = "Liliana of the Veil"
ANOINT       = "Anoint with Affliction"

# Threats
FAERIE       = "Faerie Mastermind"
RAFFINE      = "Raffine, Scheming Seer"
LOCH_WHALE   = "Horned Loch-Whale"
ARCHFIEND    = "Archfiend of the Dross"
JACE         = "Jace, the Perfected Mind"
EXCRUCIATOR  = "Doomsday Excruciator"

# Value
CRYPTIC_COAT = "Cryptic Coat"
NEGOTIATION  = "Binding Negotiation"
COVER_UP     = "Deadly Cover-Up"

_PRIO_DISRUPT = (CUT_DOWN, THROAT, LILIANA, ANOINT)
_PRIO_THREATS = (FAERIE, RAFFINE, LOCH_WHALE, JACE, ARCHFIEND, EXCRUCIATOR)
_PRIO_VALUE   = (NEGOTIATION, CRYPTIC_COAT, COVER_UP)


class EsperRaffineAPL(SBPlanMixin, BaseAPL):
    name = "Esper Raffine"
    win_condition_damage = 20
    max_turns = 14

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        disrupt = sum(1 for c in hand if c.name in _PRIO_DISRUPT)
        threats = sum(1 for c in hand if c.name in _PRIO_THREATS)
        if lands < 2 or lands >= 6:
            return False
        if 2 <= lands <= 4 and (disrupt + threats >= 2):
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[3:][:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        # Strip hand / clear board before deploying
        for name in _PRIO_DISRUPT:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        # Deploy threats cheapest-first
        for name in _PRIO_THREATS:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        # Value cards if mana left
        for name in _PRIO_VALUE:
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
