"""
apl/boros_dragons_standard.py -- Boros Dragons goldfish APL (Standard / PT SOS 2026)

W/R dragon tribal over an Azorius Tempo base.
Early curve: Momo (cost reduction for flying), Voice of Victory (tokens on attack).
Finishers: Nova Hellkite, Magmatic Hellkite, Maelstrom of the Spirit Dragon.
Clarion Conqueror buffs the team.
"""
from apl.base_apl import BaseAPL

MOMO        = "Momo, Friendly Flier"
VOICE       = "Voice of Victory"
CLARION     = "Clarion Conqueror"
NOVA        = "Nova Hellkite"
MAGMATIC    = "Magmatic Hellkite"
MAELSTROM   = "Maelstrom of the Spirit Dragon"

CURVE = (MOMO, VOICE, CLARION, NOVA, MAGMATIC, MAELSTROM)


class BorsDragonsAPL(BaseAPL):
    name = "Boros Dragons"
    win_condition_damage = 20
    max_turns = 11

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands == 0 or lands > 5:
            return False
        has_threat = any(c.name in {MOMO, VOICE, NOVA, MAGMATIC} for c in hand)
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
        momo_up = any(c.name == MOMO for c in gs.zones.battlefield)
        if momo_up:
            gs.mana_pool.cost_reduction = max(gs.mana_pool.cost_reduction, 1)
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
