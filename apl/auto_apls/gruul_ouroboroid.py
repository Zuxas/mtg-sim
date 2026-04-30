# Auto-generated APL for Gruul Ouroboroid (gemma draft)
# 2026-04-30

from data.card import Card, Tag
from apl.base_apl import BaseAPL

class GruulOuroboroidAPL(BaseAPL):
    name = "Gruul Ouroboroid"
    win_condition_damage = 20
    max_turns = 15

    def keep(self, hand: list, mulligans: int, on_play: bool) -> bool:
        # We need at least 2 lands and some early threat/removal.
        lands = [c for c in hand if c.is_land()]
        creatures = [c for c in hand if c.has(Tag.CREATURE)]
        removal = [c for c in hand if c.name == "Lightning Strike"]

        if len(hand) < 3:
            return True # Keep small hands if we can't tell
        
        # Must have enough land potential
        if len(lands) < 2:
            return False

        # Prioritize having at least one early threat or removal
        if creatures or removal:
            return True
        
        # If we have few lands but many mulligans, we might keep it.
        return mulligans >= 2 and len(lands) >= 1

    def bottom(self, hand: list, n: int) -> list:
        # Identify excess lands (keep the best 3-4)
        lands = [c for c in hand if c.is_land()]
        to_keep_lands = lands[:min(len(lands), 4)]
        excess_lands = lands[len(to_keep_lands):]

        # Identify non-land cards to keep (threats, removal)
        threats = [c for c in hand if c.name in ["Badgermole Cub", "Emberheart Challenger", "Ouroboroid", "Lightning Strike"]]
        
        # All cards that are not excess lands and not key threats
        discardable = [c for c in hand if c not in excess_lands and c not in threats]
        
        # Sort discardable by CMC descending to remove the biggest/most expensive spells first
        discardable.sort(key=lambda c: c.cmc, reverse=True)

        to_bottom = []
        
        # Fill the bottom list with excess lands first
        to_bottom.extend(excess_lands)
        
        # Then fill with discardable spells until we hit 'n'
        for card in discardable:
            if len(to_bottom) >= n:
                break
            to_bottom.append(card)
            
        return to_bottom[:n]

    def main_phase(self, gs) -> None:
        # 1. Play lands first
        self._play_land_if_able(gs)
        
        # 2. Prioritize casting cheap, aggressive creatures or removal
        hand_list = list(gs.hand())
        
        # Sort by CMC ascending to cast the cheapest threats first
        hand_list.sort(key=lambda c: c.cmc)

        for card in hand_list:
            # Check for basic threats/utility
            if card.name in ["Badgermole Cub", "Hired Claw", "Pawpatch Recruit"] and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
            
            # Use removal if we have a clear threat to deal with (simple heuristic)
            elif card.name == "Lightning Strike" and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                # Assume we are removing a threat on the board
                gs.cast_spell(card)
            
            # Cast other cheap, castable spells
            elif gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs) -> None:
        # 1. Deploy major threats (Ouroboroid)
        ouroboroid = next((c for c in gs.hand() if c.name == "Ouroboroid"), None)
        if ouroboroid and gs.mana_pool.can_cast(ouroboroid.mana_cost, ouroboroid.cmc):
            gs.cast_spell(ouroboroid)

        # 2. Deploy remaining threats/utility
        hand_list = list(gs.hand())
        hand_list.sort(key=lambda c: c.cmc)

        for card in hand_list:
            # Only cast if it's not Ouroboroid (already handled) and we can afford it
            if card.name != "Ouroboroid" and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def _play_land_if_able(self, gs):
        """Helper to play any land available."""
        lands = [c for c in gs.hand() if c.is_land()]
        if lands:
            # Play the cheapest land first
            lands.sort(key=lambda c: c.cmc)
            land_to_play = lands[0]
            if gs.mana_pool.can_cast(land_to_play.mana_cost, land_to_play.cmc):
                gs.play_land(land_to_play)