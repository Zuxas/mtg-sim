# Auto-generated APL for Mono White Aggro (decomposed-qwen2.5-coder draft)
# 2026-05-01

from data.card import Card, Tag
from apl.base_apl import BaseAPL

KEY_CARDS = {"Bitterbloom Bearer", "Get Lost", "Elspeth", "Storm Slayer"}


class MonoWhiteAggroAPL(BaseAPL):
    AUTO_GENERATED = True  # flagged for rewrite
    name = "Mono White Aggro"

    def keep(self, hand, mulligans, on_play):
        lands = [x for x in hand if x.is_land()]
        if len(hand) <= 4:
            return True
        if not lands:
            return False
        threats = [x for x in hand if x.name in ['Bitterbloom Bearer', 'Get Lost', 'Elspeth, Storm Slayer']]
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
                if c.name == "Bitterbloom Bearer" or c.name == "Get Lost":
                    gs.cast_spell(c)
                    break
                elif c.name == "Elspeth, Storm Slayer":
                    continue
                else:
                    gs.cast_spell(c)
                    break

    def main_phase2(self, gs):
        hand = gs.hand()
        battlefield = gs.zones.battlefield
        for c in sorted([x for x in hand if not x.is_land()], key=lambda x: x.cmc):
            if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                if c.name == "Requiting Hex" or c.name == "Seam Rip":
                    targets = [b for b in battlefield if b.has(Tag.CREATURE)]
                    if targets:
                        gs.cast_spell(c)
                        break
        if not any(card.name == "Elspeth, Storm Slayer" for card in battlefield):
            for c in sorted([x for x in hand if not x.is_land()], key=lambda x: x.cmc):
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc) and c.name == "Elspeth, Storm Slayer":
                    gs.cast_spell(c)
                    break