# Auto-generated APL for Landless Belcher (gemma draft)
# 2026-04-30

from data.card import Card, Tag
from apl.base_apl import BaseAPL

# Core combo pieces and high-impact spells
COMBO_PIECES = {"Lotus Bloom", "Goblin Charbelcher", "Whir of Invention", "Fallaji Archaeologist"}
INTERACTION = {"Disrupting Shoal", "Jwari Disruption", "Sink into Stupor", "Suppression Ray", "Flare of Denial", "Force of Negation", "Stern Scolding"}
RAMP_UTILITY = {"Hydroelectric Specimen", "Sea Gate Restoration", "Waterlogged Teachings", "Thundertrap Trainer", "Tameshi, Reality Architect"}
FINISHER = "Whir of Invention"

class BelcherAPL(BaseAPL):
    name = "Landless Belcher"
    win_condition_damage = 20
    max_turns = 15

    def keep(self, hand: list, mulligans: int, on_play: bool) -> bool:
        # We need at least 2 combo pieces or a strong mix of interaction/ramp.
        combo_count = sum(1 for card in hand if card.name in COMBO_PIECES)
        interaction_count = sum(1 for card in hand if card.name in INTERACTION)
        
        if combo_count >= 2:
            return True
        
        # If no combo, we need strong interaction or ramp to survive the early game.
        if interaction_count >= 3 or any(c.name in RAMP_UTILITY for c in hand):
            return True
            
        # If we are mulliganing, we can afford to be slightly weaker.
        if mulligans >= 2 and (combo_count >= 1 or interaction_count >= 2):
            return True
            
        return False

    def bottom(self, hand: list, n: int) -> list:
        # Prioritize removing high CMC, low impact spells that aren't core combo pieces.
        
        # Identify non-essential, high-cost spells
        to_bottom_candidates = [
            c for c in hand 
            if c.name not in COMBO_PIECES and c.name not in INTERACTION and c.name not in RAMP_UTILITY
            and c.cmc > 2
        ]
        
        # Sort by CMC descending to remove the biggest threats/most useless cards first
        to_bottom_candidates.sort(key=lambda c: c.cmc, reverse=True)
        
        return to_bottom_candidates[:n]

    def main_phase(self, gs) -> None:
        # 1. Use early interaction/removal if needed (e.g., dealing with threats).
        # 2. Cast the cheapest, most impactful combo pieces first.
        
        # Attempt to cast cheap interaction first
        for card in list(gs.hand()):
            if card.name in INTERACTION and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                
        # Attempt to cast core ramp/combo pieces
        for card in list(gs.hand()):
            if card.name in COMBO_PIECES and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs) -> None:
        # 1. Attempt to cast the finisher (Whir of Invention).
        # 2. Cast remaining ramp/draw spells to maximize mana/card advantage.
        
        # Try to cast the finisher first
        for card in list(gs.hand()):
            if card.name == FINISHER and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                return # Stop if we cast the finisher

        # Cast remaining ramp/utility spells
        for card in list(gs.hand()):
            if card.name in RAMP_UTILITY and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)