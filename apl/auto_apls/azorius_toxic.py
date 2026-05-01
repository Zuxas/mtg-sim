# Auto-generated APL for Azorius Toxic (decomposed-qwen2.5-coder draft)
# 2026-05-01

from data.card import Card, Tag
from apl.base_apl import BaseAPL

KEY_CARDS = {"Venerated Rotpriest", "Skrelv", "Defector Mite", "Serum Snare"}


class AzoriusToxicAPL(BaseAPL):
    name = "Azorius Toxic"

    def keep(self, hand, mulligans, on_play):
        lands = [x for x in hand if x.is_land()]
        if len(hand) <= 4:
            return True
        if not lands:
            return False
        threats = [x for x in hand if x.name in ['Venerated Rotpriest', 'Skrelv', 'Defector Mite', 'Serum Snare']]
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
                if c.name == "Serum Snare" or c.name == "Shore Up" or c.name == "Reasonable Doubt":
                    for enemy in [x for x in gs.zones.battlefield if x.has(Tag.CREATURE)]:
                        gs.cast_spell(c)
                        break
                else:
                    gs.cast_spell(c)
                    break

    def main_phase2(self, gs):
        hand = gs.hand()
        for c in sorted([x for x in hand if not x.is_land()], key=lambda x: x.cmc):
            if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                if c.name == "Venerated Rotpriest" or c.name == "Skrelv" or c.name == "Defector Mite":
                    gs.cast_spell(c)
                    break