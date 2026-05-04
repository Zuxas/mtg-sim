"""
apl/golgari_control_standard.py -- Golgari Control goldfish APL (Standard / PT SOS 2026)

G/B control. Ancient Cornucopia ramps and gains life; Deceit bounces threats;
Requiting Hex handles permanents; Firdoch Core is a graveyard payoff.
Distinct from Golgari Midrange (creature-based) and Sultai Control (U/B/G).
"""
from apl.base_apl import BaseAPL

BITTER      = "Bitter Triumph"
VIBRANCE    = "Vibrance"
CORNUCOPIA  = "Ancient Cornucopia"
DECEIT      = "Deceit"
REQUITING   = "Requiting Hex"
FIRDOCH     = "Firdoch Core"
CAVERN      = "Cavern of Souls"

CURVE = (BITTER, VIBRANCE, CORNUCOPIA, REQUITING, DECEIT, FIRDOCH)


class GolgariControlAPL(BaseAPL):
    name = "Golgari Control"
    win_condition_damage = 20
    max_turns = 14

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        return 2 <= lands <= 6

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
