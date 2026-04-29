# Auto-generated APL for Cutter Affinity (Gemma draft)
# 2026-04-28

from apl.base_apl import BaseAPL
from typing import List, Tuple

class CutterAffinity(BaseAPL):
    """
    MTG Modern APL for the 'Cutter Affinity' archetype.
    Focuses on aggressive, low-curve plays combined with removal/damage sources.
    """

    def keep(self, hand: List['Card'], mulligans: List['Card'], on_play: List['Card']) -> bool:
        """
        Decides whether to keep the hand after mulligans.
        Prioritizes early plays, interaction, and curve consistency.
        """
        # 1. Check for early plays (1-2 mana)
        early_plays = [card for card in hand if card.mana_cost <= 2]
        if not early_plays:
            return False

        # 2. Check for interaction (removal/utility)
        has_interaction = any(card.is_removal or card.is_utility for card in hand)

        # 3. Check for land count (enough to establish board presence)
        land_count = sum(1 for card in hand if card.is_land)

        # Keep if we have a mix of early plays, interaction, and enough land potential.
        if len(early_plays) >= 2 and has_interaction and land_count >= 2:
            return True
        
        # If we have a strong curve (e.g., 3+ low-cost cards) even without perfect interaction, keep it.
        if len(early_plays) >= 3 and land_count >= 1:
            return True

        return False

    def bottom(self, hand: List['Card'], n: int) -> List['Card']:
        """
        Filters the bottom 'n' cards of the hand.
        Prioritizes finding lands or low-cost interaction/creatures.
        """
        # We want to find the best 'n' cards, so we sort the hand based on utility.
        
        def card_score(card: 'Card') -> int:
            score = 0
            if card.is_land:
                score += 3  # High priority
            elif card.mana_cost <= 2:
                score += 2  # Medium priority (early plays)
            elif card.is_removal or card.is_utility:
                score += 1  # Low priority (interaction)
            return score

        # Sort the hand by score (descending)
        sorted_hand = sorted(hand, key=card_score, reverse=True)
        
        # Return the top 'n' cards from the sorted list
        return sorted_hand[:n]

    def main_phase(self, gs: 'GameState') -> Tuple[List['Card'], List['Card']]:
        """
        Plays land and then casts the most impactful spells/creatures.
        Returns (cards_to_play, cards_to_discard).
        """
        # 1. Play Land
        lands_to_play = [card for card in self.hand if card.is_land and card.mana_cost <= gs.mana_available]
        
        if lands_to_play:
            # Play the land that costs the least, or the one that is most critical (if we had that data)
            land_to_play = min(lands_to_play, key=lambda c: c.mana_cost)
            self.play_card(land_to_play)
            print(f"Playing land: {land_to_play.name}")
            
        # Update available mana after playing land
        mana_available = gs.mana_available - (land_to_play.mana_cost if 'land_to_play' in locals() else 0)

        # 2. Cast Spells/Creatures
        
        # Filter for playable cards (low cost, affordable)
        playable_cards = [card for card in self.hand if card.mana_cost <= mana_available and not card.is_land]
        
        # Prioritize:
        # 1. Removal/Interaction (to control the board)
        # 2. Low-cost, high-impact creatures (the core synergy)
        
        # Sort by impact score (simple heuristic: removal > low-cost creature > high-cost creature)
        def spell_score(card: 'Card') -> int:
            if card.is_removal or card.is_utility:
                return 3
            if card.mana_cost <= 2:
                return 2
            return 1

        playable_cards.sort(key=spell_score, reverse=True)

        cards_to_play = []
        cards_to_discard = []
        
        # Play up to 3 cards, or until mana runs out
        for card in playable_cards:
            if card.mana_cost <= mana_available:
                # Check if playing this card is beneficial (e.g., doesn't overcommit)
                if mana_available - card.mana_cost >= 0:
                    self.play_card(card)
                    cards_to_play.append(card)
                    mana_available -= card.mana_cost
                else:
                    # Cannot afford this card
                    break
            else:
                # Cannot afford this card
                break

        # If we played cards, we assume we want to keep the rest of the hand for future turns.
        # No cards are explicitly discarded unless they are lands we don't need.
        return cards_to_play, []