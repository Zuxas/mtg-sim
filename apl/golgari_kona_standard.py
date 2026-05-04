"""
apl/golgari_kona_standard.py -- Golgari Kona goldfish APL (Standard / PT SOS 2026)

G/B value midrange. Kona, Rescue Beastie recurs creatures from GY;
Vaultborn Tyrant is the top-end threat; Evendo, Waking Haven and
Susur Secundi, Void Altar provide recursive value. Requiting Hex + Deep-Cavern Bat
handle disruption.
"""
from apl.base_apl import BaseAPL

DEEP_CAVERN = "Deep-Cavern Bat"
REQUITING   = "Requiting Hex"
EVENDO      = "Evendo, Waking Haven"
SUSUR       = "Susur Secundi, Void Altar"
KONA        = "Kona, Rescue Beastie"
VAULTBORN   = "Vaultborn Tyrant"

CURVE = (DEEP_CAVERN, REQUITING, EVENDO, SUSUR, KONA, VAULTBORN)


class GolgariKonaAPL(BaseAPL):
    name = "Golgari Kona"
    win_condition_damage = 20
    max_turns = 12

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
