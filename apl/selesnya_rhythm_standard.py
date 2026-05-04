"""
apl/selesnya_rhythm_standard.py -- Selesnya Rhythm goldfish APL (Standard / PT SOS 2026)

W/G landfall-ouroboroid hybrid. Shares Badgermole Cub + Ouroboroid engine with
Selesnya Ouroboroid but runs a different support package (Gene Pollinator as
the ETB value piece vs Nass's specific Ouroboroid build). Llanowar Elves ramps
into T2 Badgermole or Ouroboroid.
"""
from apl.base_apl import BaseAPL

LLANOWAR    = "Llanowar Elves"
BADGERMOLE  = "Badgermole Cub"
GENE_POLL   = "Gene Pollinator"
OUROBOROID  = "Ouroboroid"

CURVE = (LLANOWAR, BADGERMOLE, GENE_POLL, OUROBOROID)


class SelesnyaRhythmAPL(BaseAPL):
    name = "Selesnya Rhythm"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands == 0 or lands > 5:
            return False
        has_elves = any(c.name == LLANOWAR for c in hand)
        has_cub   = any(c.name == BADGERMOLE for c in hand)
        return (has_elves or has_cub) or mulligans >= 2

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
