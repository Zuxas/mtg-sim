"""
apl/four_color_elemental_standard.py -- Four-Color Elemental goldfish APL (Standard / PT SOS 2026)

Elemental tribal using Ashling, Rekindled (recurring elemental engine),
Vibrance (elemental lord or payoff), Deceit (bounce/draw), Wistfulness
(elemental cantrip). Cavern of Souls makes elementals uncounterable.
"""
from apl.base_apl import BaseAPL

VIBRANCE    = "Vibrance"
DECEIT      = "Deceit"
WISTFULNESS = "Wistfulness"
ASHLING     = "Ashling, Rekindled"

CURVE = (VIBRANCE, WISTFULNESS, DECEIT, ASHLING)


class FourColorElementalAPL(BaseAPL):
    name = "Four-Color Elemental"
    win_condition_damage = 20
    max_turns = 11

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands < 2 or lands > 5:
            return False
        return True

    def bottom(self, hand, n):
        lands  = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[4:] + spells)[:n]

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
