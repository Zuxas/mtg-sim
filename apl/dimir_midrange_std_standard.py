"""
apl/dimir_midrange_std_standard.py -- Dimir Midrange goldfish APL (Standard / PT SOS 2026)

U/B midrange. Kaito, Bane of Nightmares is the headliner — planeswalker
that draws and creates threats. Floodpits Drowner and Spyglass Siren provide
evasive early beats. Dream Beavers and Tishana's Tidebinder provide interaction.
Distinct from Modern DimirMidrangeAPL.
"""
from apl.base_apl import BaseAPL

SIREN       = "Spyglass Siren"
TISHANA     = "Tishana's Tidebinder"
FLOODPITS   = "Floodpits Drowner"
DREAM_BEAV  = "Dream Beavers"
KAITO       = "Kaito, Bane of Nightmares"

CURVE = (SIREN, TISHANA, FLOODPITS, DREAM_BEAV, KAITO)


class DimirMidrangeStdAPL(BaseAPL):
    name = "Dimir Midrange"
    win_condition_damage = 20
    max_turns = 11

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands < 2 or lands > 5:
            return False
        has_threat = any(c.name in {SIREN, FLOODPITS, KAITO} for c in hand)
        return has_threat or mulligans >= 2

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
