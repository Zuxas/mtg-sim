# Auto-generated APL for Jeskai Phelia (gemma draft)
# 2026-04-30

from data.card import Card, Tag
from apl.base_apl import BaseAPL

# Key cards for this deck
THREATS = {"Ragavan, Nimble Pilferer", "Solitude", "Phelia, Exuberant Shepherd", "Phlage, Titan of Fire's Fury", "Teferi, Time Raveler"}
UTILITY_SPELLS = {"Consign to Memory", "Fable of the Mirror-Breaker", "March of Otherworldly Light", "Strix Serenade"}
LANDS = {"Arid Mesa", "Flooded Strand", "Scalding Tarn", "Hallowed Fountain", "Steam Vents", "Sacred Foundry", "Plains", "Island", "Mountain", "Arena of Glory", "Thundering Falls"}

class JeskaiPheliaAPL(BaseAPL):
    AUTO_GENERATED = True  # flagged for rewrite
    name = "Jeskai Phelia"
    win_condition_damage = 20
    max_turns = 15

    def keep(self, hand: list, mulligans: int, on_play: bool) -> bool:
        # We want a mix of lands, threats, and interaction.
        
        # 1. Check for basic land count
        lands = [c for c in hand if c.is_land()]
        if len(lands) < 2 and not on_play:
            return False
        
        # 2. Check for threats/utility
        threats = [c for c in hand if c.name in THREATS]
        utility = [c for c in hand if c.name in UTILITY_SPELLS]
        
        # Must have at least one threat or utility spell, unless we are on turn 1 and have lots of lands.
        if not (threats or utility):
            return False

        # If we have few cards, we keep them regardless of composition.
        if len(hand) <= 3:
            return True

        # General rule: Keep if we have enough land density and some impact.
        return len(lands) >= 2 and (threats or utility)

    def bottom(self, hand: list, n: int) -> list:
        # Prioritize putting excess lands at the bottom.
        lands = [c for c in hand if c.is_land()]
        
        # Identify excess lands (keep at least 4-5)
        excess_lands = lands[4:] if len(lands) > 4 else []
        
        # Identify non-land, non-threat, non-utility cards to put at the bottom
        low_impact_spells = [c for c in hand if not c.is_land() and c.name not in THREATS and c.name not in UTILITY_SPELLS]
        
        to_bottom = []
        
        # Add excess lands first
        for land in excess_lands:
            if len(to_bottom) < n:
                to_bottom.append(land)
            else:
                break
        
        # Fill remaining slots with low impact spells
        remaining_slots = n - len(to_bottom)
        for spell in low_impact_spells:
            if remaining_slots > 0:
                to_bottom.append(spell)
                remaining_slots -= 1
            else:
                break
                
        return to_bottom[:n]

    def main_phase(self, gs) -> None:
        # 1. Play land if possible
        self._play_land_if_able(gs)

        # 2. Cast threats/removal
        for card in list(gs.hand()):
            # Check for high-priority threats first
            if card.name in THREATS:
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    continue
            
            # Check for removal/tempo effects
            if card.name in {"Galvanic Discharge", "March of Otherworldly Light"} and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                # Assuming we target something on the battlefield if removal is castable
                if gs.zones.battlefield:
                    gs.cast_spell(card)
                    continue

    def main_phase2(self, gs) -> None:
        # 1. Utility/Card Advantage
        for card in list(gs.hand()):
            if card.name in UTILITY_SPELLS:
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    # After casting utility, we might want to check for more threats
                    break
        
        # 2. If we have mana left, cast remaining threats
        for card in list(gs.hand()):
            if card.name in THREATS:
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break