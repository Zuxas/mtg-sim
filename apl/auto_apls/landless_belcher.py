# Auto-generated APL for Landless Belcher (Gemma draft)
# 2026-04-28

from apl.base_apl import BaseAPL
from typing import List

# Assuming Card is a defined class structure within the APL environment
# For simulation purposes, we assume Card objects have methods like is_land(), is_spell(), etc.

class LandlessBelcherAPL(BaseAPL):
    """
    APL implementation for the Landless Belcher combo deck in Modern.
    Focuses on early interaction, counterspells, and setting up massive damage.
    """

    def keep(self, hand: List['Card'], mulligans: List['Card'], on_play: List['Card']) -> bool:
        """
        Determines if the hand is strong enough to keep after a mulligan.
        Prioritizes interaction and combo pieces.
        """
        
        # Count non-land spells (interaction, draw, combo enablers)
        non_land_count = sum(1 for card in hand if not card.is_land())
        
        # Check for key combo pieces (e.g., Belcher's Moon, Force of Will, etc.)
        has_key_interaction = any(
            card.name in ["Force of Will", "Mana Drain", "Ponder", "Preordain", "Belcher's Moon"] 
            for card in hand
        )

        # Keep criteria:
        # 1. High density of spells (3+ non-land cards)
        # 2. Contains a critical interaction piece, even if the count is lower.
        if non_land_count >= 3 or has_key_interaction:
            return True
        
        # If the hand is very land-heavy and lacks interaction, it's usually a poor mulligan.
        return False

    def bottom(self, hand: List['Card'], n: int) -> List['Card']:
        """
        Analyzes the bottom 'n' cards of the hand.
        Tries to find a crucial spell or a land if the current hand is weak.
        """
        bottom_cards = hand[len(hand) - n:]
        
        # Priority 1: Find a counterspell or card draw spell.
        for card in bottom_cards:
            if card.name in ["Force of Will", "Mana Drain", "Ponder", "Preordain"]:
                # Found a key piece, recommend keeping it or prioritizing it.
                return [card]

        # Priority 2: If the hand is very land-heavy and we need a spell.
        if sum(1 for card in hand if card.is_land()) > len(hand) * 0.7:
            for card in bottom_cards:
                if not card.is_land():
                    return [card]
        
        # Default: If no immediate critical piece is found, return nothing or the best available land.
        return []

    def main_phase(self, gs: dict) -> List['Card']:
        """
        Determines the optimal sequence of plays during the main phase.
        """
        hand = gs.get('hand', [])
        mana_available = gs.get('mana_available', 0)
        
        played_cards = []
        
        # 1. Play Land (Always prioritize land if possible)
        land_to_play = next((card for card in hand if card.is_land()), None)
        if land_to_play and mana_available >= 1:
            played_cards.append(land_to_play)
            # Simulate mana cost reduction
            gs['mana_available'] -= 1 
            hand.remove(land_to_play)

        # 2. Cast Spells (Prioritize interaction and combo setup)
        
        # Sort spells by perceived value (Counterspells > Draw > Combo)
        spells_to_cast = sorted(
            [card for card in hand if not card.is_land()], 
            key=lambda card: card.name, 
            reverse=True
        )

        for card in spells_to_cast:
            cost = card.get_mana_cost() # Assuming a method to get cost
            
            if cost is None:
                continue # Skip if cost cannot be determined
            
            if mana_available >= cost:
                # Check if this spell is high-impact (Counterspell, Draw, or Combo)
                if card.name in ["Force of Will", "Mana Drain", "Belcher's Moon", "Ponder"]:
                    played_cards.append(card)
                    mana_available -= cost
                    hand.remove(card)
                    # Break after casting the most impactful spell to save mana for the next turn/action
                    break 
                
                # If it's a lower priority spell, cast it if we have excess mana
                elif mana_available >= cost * 1.5: # Arbitrary check for excess mana
                    played_cards.append(card)
                    mana_available -= cost
                    hand.remove(card)
                    
        return played_cards