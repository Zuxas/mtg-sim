"""
apl/sultai_control_standard.py — Sultai Control goldfish APL (Standard)

G/U/B grind-control. Key cards: Ancient Cornucopia (ramp/gain), Deceit (bounce/draw),
Superior Spider-Man (threat), Rakshasa's Bargain (draw), Awaken the Honored Dead
(graveyard recursion), Withering Curse (drain). Kills T7-9 via attrition.
"""
from apl.base_apl import BaseAPL

CORNUCOPIA   = "Ancient Cornucopia"
DECEIT       = "Deceit"
SPIDERMAN    = "Superior Spider-Man"
BARGAIN      = "Rakshasa's Bargain"
AWAKEN       = "Awaken the Honored Dead"
WITHERING    = "Withering Curse"
EMERITUS     = "Emeritus of Ideation"
SEWERS       = "Undercity Sewers"

CURVE = (WITHERING, CORNUCOPIA, DECEIT, EMERITUS, BARGAIN, AWAKEN, SPIDERMAN)


class SultaiControlAPL(BaseAPL):
    name = "Sultai Control"
    win_condition_damage = 20
    max_turns = 14

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands < 2 or lands > 6:
            return False
        return True

    def bottom(self, hand, n):
        lands  = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[5:] + spells)[:n]

    def main_phase(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if lands and not gs.land_played:
            gs.play_land(lands[0])
        gs.tap_lands()
        for name in CURVE:
            for card in list(gs.zones.hand):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        for card in sorted(list(gs.zones.hand), key=lambda c: getattr(c, 'cmc', 0)):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs):
        gs.tap_lands()
        for card in sorted(list(gs.zones.hand), key=lambda c: getattr(c, 'cmc', 0)):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
