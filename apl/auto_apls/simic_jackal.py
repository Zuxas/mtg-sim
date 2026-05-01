# Auto-generated APL for Simic Jackal (decomposed-qwen2.5-coder draft)
# 2026-05-01

from data.card import Card, Tag
from apl.base_apl import BaseAPL

KEY_CARDS = {"Hollowmurk Siege", "Ouroboroid", "Pawpatch Recruit"}


class SimicJackalAPL(BaseAPL):
    name = "Simic Jackal"

    def keep(self, hand, mulligans, on_play):
        lands = [x for x in hand if x.is_land()]
        if len(hand) <= 4:
            return True
        if not lands:
            return False
        threats = [x for x in hand if x.name in ['Hollowmurk Siege', 'Ouroboroid', 'Pawpatch Recruit']]
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
                if c.name == "Hollowmurk Siege" or c.name == "Ouroboroid":
                    gs.cast_spell(c)
                    break
                elif c.has(Tag.CREATURE):
                    gs.cast_spell(c)

    def main_phase2(self, gs):
        hand = gs.hand()
        battlefield = gs.zones.battlefield
        for c in sorted([x for x in hand if not x.is_land()], key=lambda x: x.cmc):
            if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                if c.name == "Requiting Hex" or c.name == "Scavenging Ooze":
                    targets = [card for card in battlefield if card.has(Tag.CREATURE) and not getattr(card, "tapped", False)]
                    if targets:
                        gs.cast_spell(c)
                        break