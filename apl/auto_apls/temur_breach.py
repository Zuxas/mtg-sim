# Auto-generated APL for Temur Breach (decomposed-qwen2.5-coder draft)
# 2026-06-26

from data.card import Card, Tag
from apl.base_apl import BaseAPL

KEY_CARDS = {"Lightning Strike", "Inferno Titan", "Bolt"}


class TemurBreachAPL(BaseAPL):
    name = "Temur Breach"

    def keep(self, hand, mulligans, on_play):
        lands = [x for x in hand if x.is_land()]
        if len(hand) <= 4:
            return True
        if not lands:
            return False
        threats = [x for x in hand if x.name in ['Lightning Strike', 'Inferno Titan', 'Bolt']]
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
                if c.has(Tag.CREATURE) and (c.name == "Lightning Strike" or c.name == "Bolt"):
                    gs.cast_spell(c)
                    break
                elif c.name == "Inferno Titan":
                    gs.cast_spell(c)
                    break
                else:
                    gs.cast_spell(c)

    def main_phase2(self, gs):
        battlefield = gs.zones.battlefield
        for c in battlefield:
            if c.has(Tag.CREATURE) and c.power is not None and c.toughness is not None:
                if int(c.power) > 0:
                    for x in [y for y in gs.hand() if y.name == "Path to Exile"]:
                        if gs.mana_pool.can_cast(x.mana_cost, x.cmc):
                            gs.cast_spell(x)
                            break