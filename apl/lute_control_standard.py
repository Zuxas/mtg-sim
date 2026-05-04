"""
apl/lute_control_standard.py -- Resonating Lute control shell (Standard / PT SOS 2026)

Shared engine: Resonating Lute tutors instants/sorceries; pairs with
Flashback (recur from GY), Consult the Star Charts (scry+draw),
Great Hall of the Biblioplex (lesson tutor). Wins via Colorstorm
Stallion beats or control inevitability.

Temur Lute: G/U/R  | Four-Color Control: W/U/B/R (adds white removal)
"""
from apl.base_apl import BaseAPL

LUTE       = "Resonating Lute"
CONSULT    = "Consult the Star Charts"
GREAT_HALL = "Great Hall of the Biblioplex"
FLASHBACK  = "Flashback"
STALLION   = "Colorstorm Stallion"
FIREBEND   = "Firebending Lesson"
REVELATION = "Jeskai Revelation"
INEVITABLE = "Inevitable Defeat"
STOCK_UP   = "Stock Up"
NO_MORE    = "No More Lies"

CURVE = (LUTE, CONSULT, STOCK_UP, GREAT_HALL, FLASHBACK,
         FIREBEND, STALLION, REVELATION, INEVITABLE)


class LuteControlAPL(BaseAPL):
    name = "Lute Control"
    win_condition_damage = 20
    max_turns = 14

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands < 2 or lands > 6:
            return False
        has_lute = any(c.name == LUTE for c in hand)
        return has_lute or mulligans >= 2

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


class TemurLuteAPL(LuteControlAPL):
    name = "Temur Lute"


class FourColorControlAPL(LuteControlAPL):
    name = "Four-Color Control"
