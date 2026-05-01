# Auto-generated APL for Simic Rhythm (decomposed-qwen2.5-coder draft)
# 2026-05-01

from data.card import Card, Tag
from apl.base_apl import BaseAPL

KEY_CARDS = {"Nature's Rhythm", "Quantum Riddler", "Mockingbird"}


class SimicRhythmAPL(BaseAPL):
    name = "Simic Rhythm"

    def keep(self, hand, mulligans, on_play):
        lands = [x for x in hand if x.is_land()]
        if len(hand) <= 4:
            return True
        if not lands:
            return False
        threats = [x for x in hand if x.name in ['Nature\'s Rhythm', 'Quantum Riddler', 'Mockingbird']]
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
        ramp_spells = [x for x in hand if not x.is_land() and (x.name == "Nature's Rhythm" or x.name == "Quantum Riddler")]
        threats = [x for x in hand if not x.is_land() and (x.name == "Mockingbird" or x.name == "Surrak, Elusive Hunter" or x.name == "Keen-Eyed Curator")]

        # Play ramp spells first
        for c in sorted(ramp_spells, key=lambda x: x.cmc):
            if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

    def main_phase2(self, gs):
        hand = gs.hand()
        threats = [x for x in hand if not x.is_land() and (x.name == "Mockingbird" or x.name == "Surrak, Elusive Hunter" or x.name == "Keen-Eyed Curator")]

        # Cast big threats
        for c in sorted(threats, key=lambda x: x.cmc):
            if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break