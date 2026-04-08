"""apl/domain_zoo.py — Domain Zoo APL (Modern)
Ragavan + Territorial Kavu + Phlage + Scion of Draco.
Leyline of the Guildpact enables full domain on T1.
Kill clock: T3-4 aggressive beatdown.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState

RAGAVAN  = "Ragavan, Nimble Pilferer"
KAVU     = "Territorial Kavu"
PHLAGE   = "Phlage, Titan of Fire's Fury"
SCION    = "Scion of Draco"
LEYLINE_G= "Leyline of the Guildpact"
LEYLINE_B= "Leyline Binding"
FABLE    = "Fable of the Mirror-Breaker"
BOLT     = "Lightning Bolt"
DENIAL   = "Stubborn Denial"
PRISMATIC= "Prismatic Ending"
CONSIGN  = "Consign to Memory"

class DomainZooAPL(SBPlanMixin, BaseAPL):
    name = "Domain Zoo"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands   = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in {RAGAVAN, KAVU, PHLAGE, SCION})
        has_ley = any(c.name == LEYLINE_G for c in hand)
        if lands == 0: return False
        if lands >= 2 and threats >= 1: return True
        if has_ley and threats >= 1 and lands >= 1: return True  # Leyline + 1 land keep
        return len(hand) <= 5 or mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[3:][:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        # Deploy Leyline if in hand (free in opening but model as T1 play)
        for card in list(gs.hand()):
            if card.name == LEYLINE_G and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                gs._log("  Leyline of the Guildpact → full domain enabled")
                break
        # Threats by priority
        for name in (RAGAVAN, KAVU, SCION, PHLAGE, FABLE):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        # Removal / interaction
        for card in list(gs.hand()):
            if card.name == BOLT and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.damage_dealt += 3
                gs.hand().remove(card)
                gs.zones.graveyard.append(card)
                gs._log("  Lightning Bolt → face (3)")
                break
        for card in list(gs.hand()):
            if card.name in {PRISMATIC, LEYLINE_B} and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
