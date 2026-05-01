# Auto-generated APL for Cutter Affinity (decomposed-qwen2.5-coder draft)
# 2026-04-30

from data.card import Card, Tag
from apl.base_apl import BaseAPL


class CutterAffinityAPL(BaseAPL):
    name = "Cutter Affinity"

    def keep(self, hand, mulligans, on_play):
        lands = [c for c in hand if c.is_land()]
        if len(hand) <= 4:
            return True
        if not lands:
            return False
        return len(lands) >= 2

    def bottom(self, hand, n):
        excess = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        to_bottom = excess[2:] if len(excess) > 2 else []
        high_cmc = sorted([c for c in hand if not c.is_land() and c not in to_bottom],
                          key=lambda c: -c.cmc)
        for s in high_cmc:
            if len(to_bottom) >= n:
                break
            to_bottom.append(s)
        return to_bottom[:n]

    def main_phase(self, gs):
        self._play_land_if_able(gs)
        hand = gs.hand()
        threats = [c for c in hand if not c.is_land() and (c.has(Tag.CREATURE) or c.has(Tag.INSTANT) or c.has(Tag.SORCERY))]
        removals = [c for c in hand if not c.is_land() and not c.has(Tag.CREATURE) and not c.has(Tag.INSTANT) and not c.has(Tag.SORCERY)]

        for card in sorted(threats, key=lambda c: c.cmc):
            if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break

    def main_phase2(self, gs):
        hand = gs.hand()
        threats = [c for c in hand if not c.is_land() and (c.has(Tag.CREATURE) or c.has(Tag.INSTANT) or c.has(Tag.SORCERY))]
        removals = [c for c in hand if not c.is_land() and not c.has(Tag.CREATURE) and not c.has(Tag.INSTANT) and not c.has(Tag.SORCERY)]

        for card in sorted(removals, key=lambda c: c.cmc):
            if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break