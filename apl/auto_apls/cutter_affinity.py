# Auto-generated APL for Cutter Affinity (Gemma draft)
# 2026-04-29

from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL

# Assuming "Cutter Affinity" focuses on low-cost, synergistic, aggressive creatures
# We define placeholder threats that represent the core synergy pieces.
# In a real scenario, these would be specific card names (e.g., "Goblin Guide", "Swarm").
SYNERGY_THREATS = {"Goblin", "Swarm", "Affinity"}

class CutterAffinityAPL(BaseAPL):
    name = "Cutter Affinity"
    win_condition_damage = 25
    max_turns = 10

    def keep(self, hand: list, mulligans: int, on_play: bool) -> bool:
        """
        Keep hands that are aggressive, land-rich, and contain multiple low-cost threats.
        """
        lands = [c for c in hand if c.is_land()]
        
        # Must have at least 2 lands to start establishing board presence
        if len(lands) < 2:
            return False

        # Identify low-cost, synergistic threats (CMC <= 3)
        threats = [c for c in hand if c.cmc <= 3 and any(tag in c.name for tag in SYNERGY_THREATS)]
        
        # We need at least 2 threats or enough mulligans to compensate for a weak hand
        if len(threats) >= 2:
            return True
        
        # If we only have one threat, we need a decent mulligan count
        if len(threats) == 1 and mulligans >= 2:
            return True
        
        # Otherwise, the hand is too slow or lacks synergy
        return False

    def bottom(self, hand: list, n: int) -> list:
        """
        Prioritize bottoming excess lands and high-cost, non-synergistic spells.
        """
        lands = [c for c in hand if c.is_land()]
        
        # 1. Excess Lands: Keep the first 3-4 lands, bottom the rest.
        to_bottom = lands[4:]
        
        # 2. High CMC, non-synergistic cards
        remaining_cards = [c for c in hand if c not in to_bottom]
        
        # Sort by CMC descending, then by name (to ensure deterministic removal)
        high_cmc_spells = sorted(
            [c for c in remaining_cards if c.cmc > 3 and not any(tag in c.name for tag in SYNERGY_THREATS)],
            key=lambda c: (c.cmc, c.name), reverse=True
        )
        
        # Combine and limit to n
        to_bottom.extend(high_cmc_spells)
        return to_bottom[:n]

    def main_phase(self, gs: GameState) -> None:
        """
        Play all available lands and cast the cheapest, most synergistic threats.
        """
        # 1. Play Lands
        lands_to_play = [c for c in gs.hand() if c.is_land()]
        for land in lands_to_play:
            if gs.mana_pool.can_cast(land.mana_cost, land.cmc):
                gs.play_land(land)

        # 2. Cast Threats (Prioritize cheapest first)
        threats = [c for c in gs.hand() if c.cmc <= 3 and any(tag in c.name for tag in SYNERGY_THREATS)]
        # Sort by CMC ascending
        threats.sort(key=lambda c: c.cmc)

        for card in threats:
            if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs: GameState) -> None:
        """
        Cast any remaining affordable threats or utility spells.
        """
        # Identify all remaining threats (regardless of cost, if affordable)
        all_threats = [c for c in gs.hand() if any(tag in c.name for tag in SYNERGY_THREATS)]
        
        # Sort by CMC ascending to maximize casting potential
        all_threats.sort(key=lambda c: c.cmc)

        for card in all_threats:
            if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
            else:
                # Optimization: If the card is too expensive now, assume subsequent cards are also too.
                # This is a heuristic, but helps prevent unnecessary checks.
                if card.cmc > 5:
                    break