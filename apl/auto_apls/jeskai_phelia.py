# Auto-generated APL for Jeskai Phelia (Gemma draft)
# 2026-04-28

from apl.base_apl import BaseAPL
from typing import List

class JeskaiPhelia(BaseAPL):
    """
    APL implementation for the Jeskai Phelia Modern deck.
    Focuses on tempo, interaction, and efficient threats.
    """

    def keep(self, hand: List['Card'], mulligans: List[str], on_play: bool) -> bool:
        """
        Determines if the hand should be kept after a mulligan.
        Prioritizes balance: land drops, interaction, and early threats.
        """
        if not hand:
            return False

        # Basic check: Ensure we have at least 2-3 lands and some interaction.
        land_count = sum(1 for card in hand if card.is_land())
        interaction_count = sum(1 for card in hand if card.is_spell() and card.is_interaction())

        if land_count < 2:
            return False

        # If we have too many lands (e.g., > 5) and no spells, it's bad.
        if land_count > 5 and interaction_count == 0:
            return False

        # If we have a decent mix (2-3 lands, 2+ interaction, 1-2 threats), keep it.
        if 2 <= land_count <= 4 and interaction_count >= 2:
            return True

        # Fallback: If the hand is otherwise balanced, keep it.
        return True

    def bottom(self, hand: List['Card'], n: int) -> List['Card']:
        """
        Predicts the cards at the bottom of the library.
        Assumes a mix, but avoids bottoming out on too much non-land filler.
        """
        # In a tempo deck, we want to ensure we don't bottom out on too many non-playable lands
        # or too many high-cost, non-interactive spells.
        
        # Since we cannot predict the exact distribution, we assume a balanced draw.
        # We return a list of placeholder cards representing the expected draw.
        
        # Placeholder logic: Assume a mix of 1 land, 1 interaction, 1 threat per 3 cards.
        predicted_bottom = []
        for i in range(n):
            if i % 3 == 0:
                # Land
                predicted_bottom.append(self._get_placeholder_land())
            elif i % 3 == 1:
                # Interaction/Draw
                predicted_bottom.append(self._get_placeholder_spell("Counterspell"))
            else:
                # Threat/Mid-cost spell
                predicted_bottom.append(self._get_placeholder_spell("Efficient Threat"))
        
        return predicted_bottom

    def main_phase(self, gs: 'GameState') -> None:
        """
        Plays land, then prioritizes interaction and efficient threats.
        """
        # 1. Play Land
        land_to_play = next((card for card in self.hand if card.is_land() and card.mana_cost <= gs.available_mana), None)
        if land_to_play:
            self.play_card(land_to_play)
            gs.available_mana += 2 # Assuming basic land drop
        
        # 2. Prioritize Interaction (Counterspells/Removal)
        # Check for immediate threats or opponent's setup that needs disruption.
        interaction_cards = [card for card in self.hand if card.is_spell() and card.is_interaction() and card.mana_cost <= gs.available_mana]
        
        if interaction_cards:
            # Play the most efficient interaction first (lowest cost, highest impact)
            interaction_cards.sort(key=lambda c: c.mana_cost)
            card_to_play = interaction_cards[0]
            self.play_card(card_to_play)
            gs.available_mana -= card_to_play.mana_cost

        # 3. Play Threats/Card Advantage
        # If interaction was used, or if the board is clear, play the best threat.
        threats = [card for card in self.hand if card.is_threat() and card.mana_cost <= gs.available_mana]
        
        if threats:
            # Play the most efficient threat (e.g., lowest cost, highest power/toughness ratio)
            threats.sort(key=lambda c: c.mana_cost)
            card_to_play = threats[0]
            self.play_card(card_to_play)
            gs.available_mana -= card_to_play.mana_cost
        
        # 4. Card Draw/Filtering (If resources remain)
        # If we have mana left and haven't played a major threat, look for card draw.
        draw_spells = [card for card in self.hand if card.is_spell() and card.is_draw() and card.mana_cost <= gs.available_mana]
        if draw_spells and gs.available_mana >= 1:
            # Play the cheapest draw spell
            draw_spells.sort(key=lambda c: c.mana_cost)
            card_to_play = draw_spells[0]
            self.play_card(card_to_play)
            gs.available_mana -= card_to_play.mana_cost

    # --- Helper Methods (Mocking Card/Game State Logic) ---
    
    def _get_placeholder_land(self) -> 'Card':
        """Mock function for a land card."""
        class MockLand:
            def is_land(self): return True
            def mana_cost(self): return 0
        return MockLand()

    def _get_placeholder_spell(self, name: str) -> 'Card':
        """Mock function for a spell card."""
        class MockSpell:
            def __init__(self, name, cost):
                self.name = name
                self.mana_cost = cost
            def is_spell(self): return True
            def is_interaction(self): return "Counterspell" in self.name or "Removal" in self.name
            def is_threat(self): return False
            def is_draw(self): return "Draw" in self.name
            def is_land(self): return False
            
        if "Counterspell" in name:
            return MockSpell(name, 1)
        elif "Removal" in name:
            return MockSpell(name, 2)
        elif "Draw" in name:
            return MockSpell(name, 1)
        elif "Efficient Threat" in name:
            return MockSpell(name, 2)
        return MockSpell(name, 3)
```