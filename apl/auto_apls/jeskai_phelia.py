# Auto-generated APL for Jeskai Phelia (Gemma draft)
# 2026-04-29

from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL

# Jeskai Phelia focuses on tempo, counterspells, and burn/direct damage.
# Key threats/interactions include efficient flyers, cheap removal, and card advantage engines.
CORE_THREATS = {"Aethermage's Volition", "Counterspell", "Lightning Bolt", "Skyclave Apparition", "Shock"}

class JeskaiAPL(BaseAPL):
    name = "Jeskai Phelia"
    win_condition_damage = 20
    max_turns = 15

    def keep(self, hand: list, mulligans: int, on_play: bool) -> bool:
        """
        Keep a hand if it has enough lands and a mix of interaction/threats.
        """
        lands = [c for c in hand if c.is_land()]
        
        # Minimum requirement: 2 lands, at least one interaction piece, and some threats.
        if len(lands) < 2:
            return False
        
        interaction_count = sum(1 for c in hand if c.name in CORE_THREATS and c.mana_cost != "{0}")
        
        if interaction_count == 0 and mulligans < 2:
            return False
        
        # If we have few cards, we are likely fine, unless we have zero lands.
        if len(hand) <= 3:
            return True
            
        # General check: Need a balance of resources.
        return len(lands) >= 2 and interaction_count >= 1

    def bottom(self, hand: list, n: int) -> list:
        """
        Bottom the excess lands and the highest CMC, lowest impact spells.
        """
        lands = [c for c in hand if c.is_land()]
        
        # 1. Excess lands (keep at least 3-4)
        excess_lands = lands[3:] if len(lands) > 3 else []
        
        # 2. Non-land cards: Sort by CMC descending, then by name (to ensure deterministic removal)
        non_lands = [c for c in hand if not c.is_land() and c not in excess_lands]
        
        # Prioritize removing high CMC, non-essential spells/creatures
        high_cmc_to_remove = sorted(non_lands, key=lambda c: (-c.cmc, c.name))
        
        to_bottom = []
        
        # Combine excess lands and high-CMC spells
        for i in range(min(n, len(excess_lands) + len(high_cmc_to_remove))):
            if i < len(excess_lands):
                to_bottom.append(excess_lands[i])
            else:
                to_bottom.append(high_cmc_to_remove[i - len(excess_lands)])
                
        return to_bottom

    def main_phase(self, gs: GameState) -> None:
        """
        Early game phase: Prioritize playing lands and cheap, efficient interaction.
        """
        # 1. Play land if possible
        self._play_land_if_able(gs)
        
        # 2. Play cheap interaction/threats (CMC 1-3)
        for card in list(gs.hand()):
            if card.is_land():
                continue
            
            # Check for low-cost, high-impact spells (e.g., 1-2 CMC counterspells or burn)
            if card.cmc <= 3 and card.mana_cost != "{0}":
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    # Prioritize counterspells/removal first
                    if card.name in CORE_THREATS and card.has(Tag.INSTANT):
                        gs.cast_spell(card)
                        continue
                    
                    # Otherwise, cast if it's cheap and useful
                    gs.cast_spell(card)
                    
    def main_phase2(self, gs: GameState) -> None:
        """
        Late game phase: Focus on closing the game with burn or countering major threats.
        """
        # 1. Counter the biggest threat on the board if we can afford it
        for card in list(gs.zones.battlefield):
            if card.name in CORE_THREATS and card.has(Tag.CREATURE) and card.cmc > 3:
                if gs.mana_pool.can_cast("{U}", card.cmc): # Assuming Blue counterspell
                    gs.cast_spell(Card("Counterspell", "{U}", 2, "Counterspell", Tag.INSTANT))
                    break
        
        # 2. Burn down the opponent if we have direct damage spells
        for card in list(gs.hand()):
            if card.name in CORE_THREATS and card.mana_cost == "{R}" and card.has(Tag.SORCERY):
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        
        # 3. Otherwise, cast the most expensive, impactful spell we can afford
        best_card = None
        max_cmc = -1
        for card in list(gs.hand()):
            if not card.is_land() and card.cmc > 0:
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    if card.cmc > max_cmc:
                        max_cmc = card.cmc
                        best_card = card
        
        if best_card:
            gs.cast_spell(best_card)