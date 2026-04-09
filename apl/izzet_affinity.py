"""
izzet_affinity.py — APL for Modern Affinity

Key: dump 0-cost artifacts T1, Cranial Plating for huge damage.
Plating gives +1/+0 per artifact you control.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL

ZERO_DROPS = {"Ornithopter", "Memnite", "Mox Opal", "Mishra's Bauble", "Welding Jar"}
PLATING = "Cranial Plating"
SIGNAL_PEST = "Signal Pest"
STEEL_OVERSEER = "Steel Overseer"


class IzzetAffinityAPL(BaseAPL):
    name = "Izzet Affinity"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        lands = [c for c in hand if c.is_land()]
        zeros = [c for c in hand if c.name in ZERO_DROPS]
        if len(hand) <= 4: return True
        if not lands and not any(c.name == "Mox Opal" for c in hand): return False
        # Affinity wants lots of cheap artifacts + payoff
        if len(zeros) >= 2 and lands: return True
        if any(c.name == PLATING for c in hand) and len(zeros) >= 1: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        to_bottom = []
        if len(lands) > 2: to_bottom.extend(lands[2:])
        rest = sorted([c for c in hand if not c.is_land()], key=lambda c: -c.cmc)
        for c in rest:
            if len(to_bottom) >= n: break
            if c not in to_bottom: to_bottom.append(c)
        return to_bottom[:n]

    def main_phase(self, gs):
        """Dump hand: land, 0-drops, then threats."""
        self._play_land_if_able(gs)
        # 0-drops first (free)
        for card in list(gs.hand()):
            if card.name in ZERO_DROPS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                # Mox Opal: metalcraft → add 1 flex mana
                if card.name == "Mox Opal":
                    artifacts = sum(1 for c in gs.zones.battlefield
                                   if "artifact" in c.type_line.lower())
                    if artifacts >= 3:
                        gs.mana_pool.flex += 1
        # Cranial Plating (2 mana)
        for card in list(gs.hand()):
            if card.name == PLATING and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
        # Other creatures
        self._cast_all_castable(gs, Tag.CREATURE)

    def main_phase2(self, gs):
        """Post-combat: simulate Plating damage bonus and cast remaining."""
        # Cranial Plating: equipped creature gets +N/+0 where N = artifact count
        # In goldfish: add artifact count to combat damage retroactively
        platings = sum(1 for c in gs.zones.battlefield if c.name == PLATING)
        if platings > 0:
            artifacts = sum(1 for c in gs.zones.battlefield
                           if "artifact" in c.type_line.lower())
            # Plating bonus was already missed in combat... apply as extra damage
            # (simplified: Plating gives +artifacts power to one creature's combat damage)
            bonus = platings * artifacts
            gs.damage_dealt += bonus
            gs._log(f"  Cranial Plating: +{bonus} dmg ({platings} plating, {artifacts} artifacts)")

        # Galvanic Blast: 4 damage with metalcraft
        for card in list(gs.hand()):
            if card.name == "Galvanic Blast" and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                artifacts = sum(1 for c in gs.zones.battlefield
                               if "artifact" in c.type_line.lower())
                dmg = 4 if artifacts >= 3 else 2
                gs.cast_spell(card)
                gs.damage_dealt += dmg
                gs._log(f"  Galvanic Blast: {dmg} dmg ({gs.damage_dealt} total)")
                break

        self._cast_all_castable(gs)
