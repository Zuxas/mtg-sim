# Auto-generated APL for Gruul Ouroboroid (gemma draft)
# 2026-04-30

from data.card import Card, Tag
from apl.base_apl import BaseAPL

class GruulOuroboroidAPL(BaseAPL):
    AUTO_GENERATED = True  # flagged for rewrite
    name = "Gruul Ouroboroid"
    win_condition_damage = 20
    max_turns = 15

    def keep(self, hand: list, mulligans: int, on_play: bool) -> bool:
        lands = [c for c in hand if c.is_land()]
        spells = [c for c in hand if not c.is_land()]
        
        # Must have at least 2 lands to establish a board presence
        if len(lands) < 2:
            return False
        
        # Prioritize having a mix of threats and interaction
        threats = [c for c in hand if c.name in ["Emberheart Challenger", "Badgermole Cub", "Pawpatch Recruit"]]
        
        # If we have enough lands and at least one threat or utility spell, we keep it.
        if len(lands) >= 2 and (threats or any(c.name in ["Lightning Strike", "Overprotect", "Hired Claw"] for c in spells)):
            return True
        
        # If we are mulliganing, keep it if we have a decent land count.
        if mulligans > 0 and len(lands) >= 2:
            return True
            
        return False

    def bottom(self, hand: list, n: int) -> list:
        # Sort lands to put the least useful ones (if any) at the top of the bottom list
        lands = [c for c in hand if c.is_land()]
        
        # Identify non-land cards, prioritizing high CMC threats/spells to keep
        non_lands = [c for c in hand if not c.is_land()]
        
        # We want to bottom the lowest impact cards first.
        # Criteria: Low CMC, non-threat, non-utility.
        
        # Sort by CMC (ascending) and then by name (alphabetical)
        to_bottom_candidates = sorted(non_lands, key=lambda c: (c.cmc, c.name))
        
        # If we have too many lands, we might bottom some, but generally, we want to keep the lands.
        # Since we are limited to n cards, we take the lowest impact ones.
        
        return to_bottom_candidates[:n]

    def main_phase(self, gs) -> None:
        # 1. Play lands first
        self._play_land_if_able(gs)
        
        # 2. Prioritize casting threats/creatures
        threats = ["Emberheart Challenger", "Badgermole Cub", "Pawpatch Recruit"]
        
        # Attempt to cast threats in order of lowest cost/highest impact
        for card in list(gs.hand()):
            if card.name in threats:
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    
        # 3. Use interaction/utility spells if possible (e.g., Lightning Strike)
        for card in list(gs.hand()):
            if card.name in ["Lightning Strike", "Overprotect", "Hired Claw"]:
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)

    def main_phase2(self, gs) -> None:
        # 1. Play remaining lands
        self._play_land_if_able(gs)
        
        # 2. Cast utility/removal spells (e.g., Hexing Squelcher, Impolite Entrance)
        utility_spells = ["Hexing Squelcher", "Impolite Entrance", "Might of the Meek"]
        for card in list(gs.hand()):
            if card.name in utility_spells:
                if gs.mana_pool.cancast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
        
        # 3. Cast remaining threats/creatures
        threats = ["Emberheart Challenger", "Badgermole Cub", "Pawpatch Recruit"]
        for card in list(gs.hand()):
            if card.name in threats:
                if gs.mana_pool.cancast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)