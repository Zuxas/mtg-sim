# Auto-generated APL for Boros Energy (decomposed-qwen2.5-coder draft)
# 2026-06-26

from data.card import Card, Tag
from apl.base_apl import BaseAPL

KEY_CARDS = {"Phlage", "Titan of Fire's Fury", "Ragavan", "Nimble Pilferer", "Seasoned Pyromancer"}


class BorosEnergyAPL(BaseAPL):
    name = "Boros Energy"

    def keep(self, hand, mulligans, on_play):
        lands = [x for x in hand if x.is_land()]
        if len(hand) <= 4:
            return True
        if not lands:
            return False
        threats = [x for x in hand if x.name in ['Phlage', 'Titan of Fire\'s Fury', 'Ragavan', 'Nimble Pilferer', 'Seasoned Pyromancer']]
        return len(lands) >= 2 and (threats or mulligans >= 2)

    def bottom(self, hand, n):
        excess = sorted([x for x in hand if x.is_land()], key=lambda x: x.name)
        to_bottom = excess[3:] if len(excess) > 3 else []
        high_cmc = sorted([x for x in hand if not x.is_land() and x not in to_bottom],
                          key=lambda x: -x.cmc)
        for s in high_cmc:
            if len(to_bottom) >= n:
                break
            to_bottom.append(s)
        return to_bottom[:n]

    def main_phase(self, gs):
        self._play_land_if_able(gs)
        hand = gs.hand()
        for c in sorted([x for x in hand if not x.is_land()], key=lambda x: x.cmc):
            if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

    def main_phase2(self, gs):
        battlefield = gs.zones.battlefield
        hand = gs.hand()

        # Play removal spells on blockers
        for c in sorted([x for x in hand if x.has(Tag.INSTANT) or x.has(Tag.SORCERY)], key=lambda x: x.cmc):
            if any(card.power and card.toughness for card in battlefield):
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # Play creatures
        for c in sorted([x for x in hand if x.has(Tag.CREATURE)], key=lambda x: x.cmc):
            if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)