"""
apl/bant_rhythm_standard.py -- Bant Rhythm goldfish APL (Standard / PT SOS 2026)

W/G/U landfall creature base. Badgermole Cub grows on landfall; Llanowar Elves
accelerates. Quantum Riddler provides card selection; Seam Rip bounces own
permanents for re-ETBs. Distinct from Simic Cub (no Ouroboroid engine,
has white for Seam Rip interaction).
"""
from apl.base_apl import BaseAPL

LLANOWAR    = "Llanowar Elves"
BADGERMOLE  = "Badgermole Cub"
SEAM_RIP    = "Seam Rip"
QUANTUM     = "Quantum Riddler"

CURVE = (LLANOWAR, BADGERMOLE, SEAM_RIP, QUANTUM)


class BantRhythmAPL(BaseAPL):
    name = "Bant Rhythm"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands == 0 or lands > 5:
            return False
        has_early = any(c.name in {LLANOWAR, BADGERMOLE} for c in hand)
        return has_early or mulligans >= 2

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
