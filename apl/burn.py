"""
burn.py — APL for Modern Burn (mapped from 'Mono Red Aggro' in field)

Every spell goes face. Haste creatures attack immediately.
Goldfish kill: T3-4 with good draws.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL

# Face damage spells
FACE_SPELLS = {
    "Lightning Bolt": 3, "Lava Spike": 3, "Rift Bolt": 3,
    "Skewer the Critics": 3, "Boros Charm": 4, "Lightning Helix": 3,
    "Searing Blaze": 3, "Skullcrack": 3, "Roiling Vortex": 0,  # enchantment, 1/turn
}
HASTE_CREATURES = {"Goblin Guide", "Monastery Swiftspear", "Eidolon of the Great Revel"}


class BurnAPL(BaseAPL):
    name = "Burn"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        lands = [c for c in hand if c.is_land()]
        spells = [c for c in hand if not c.is_land()]
        if len(hand) <= 4: return True
        if not lands: return False
        if len(lands) > 3: return False
        # Need damage sources
        damage = sum(FACE_SPELLS.get(c.name, 0) for c in spells)
        damage += sum(2 for c in spells if c.name in HASTE_CREATURES)
        return damage >= 6 or mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        to_bottom = []
        if len(lands) > 2:
            to_bottom.extend(lands[2:])
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: FACE_SPELLS.get(c.name, 0))
        for s in spells:
            if len(to_bottom) >= n: break
            if s not in to_bottom: to_bottom.append(s)
        return to_bottom[:n]

    def _best_land(self, gs):
        lands = [c for c in gs.hand() if c.is_land()]
        if not lands: return None
        # Fetches first, then untapped, then basics
        def score(c):
            n = c.name.lower()
            if "mesa" in n or "mire" in n or "canyon" in n or "strand" in n: return 0
            if "inspiring vantage" in n: return 1
            if "sacred foundry" in n: return 2
            if "mountain" in n: return 3
            return 4
        return min(lands, key=score)

    def main_phase(self, gs):
        """Pre-combat: land, haste creatures."""
        self._play_land_if_able(gs)
        # Cast haste creatures pre-combat
        for card in list(gs.hand()):
            if card.name in HASTE_CREATURES and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs):
        """Post-combat: burn face with everything."""
        # Prowess: count spells cast this turn for Swiftspear pump
        # (simplified — just cast everything and add face damage)
        for card in list(gs.hand()):
            if card.is_land(): continue
            name = card.name
            if name in FACE_SPELLS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                dmg = FACE_SPELLS[name]
                if dmg > 0:
                    gs.damage_dealt += dmg
                    gs._log(f"  {name} face: {dmg} dmg ({gs.damage_dealt} total)")
            elif card.has(Tag.CREATURE) and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

        # Roiling Vortex: 1 damage per upkeep (track it)
        vortexes = sum(1 for c in gs.zones.battlefield if c.name == "Roiling Vortex")
        if vortexes:
            gs.damage_dealt += vortexes
            gs._log(f"  Roiling Vortex: {vortexes} dmg ({gs.damage_dealt} total)")
