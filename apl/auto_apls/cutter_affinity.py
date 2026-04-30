# Auto-generated APL for Cutter Affinity (gemma draft)
# 2026-04-30

from data.card import Card, Tag
from apl.base_apl import BaseAPL

# Key artifacts and synergy pieces for Cutter Affinity
ARTIFACT_STARS = {"Mox Opal", "Mox Amber", "Mishra's Bauble", "Emry, Lurker of the Loch", "Cori-Steel Cutter"}
LANDS = {"Scalding Tarn", "Steam Vents", "Breeding Pool", "Otawara, Soaring City", "Spirebluff Canal", "Strix Serenade", "Thundering Falls", "Island", "Mountain"}

class CutterAffinityAPL(BaseAPL):
    name = "Cutter Affinity"
    win_condition_damage = 20
    max_turns = 15

    def keep(self, hand: list, mulligans: int, on_play: bool) -> bool:
        # We want a mix of lands and low-cost artifacts/spells.
        
        lands = [c for c in hand if c.is_land()]
        artifacts = [c for c in hand if c.name in ARTIFACT_STARS]
        low_cost_spells = [c for c in hand if c.cmc <= 3 and not c.is_land()]
        
        # Minimum requirements: 2 lands, and at least 2 synergistic cards (artifact or low-cost spell)
        if len(lands) < 2:
            return False
        
        if not (artifacts or low_cost_spells):
            return False
            
        # If we have enough synergy and land, keep it.
        return True

    def bottom(self, hand: list, n: int) -> list:
        # Prioritize dumping excess lands first.
        excess_lands = [c for c in hand if c.is_land()]
        
        # Sort by name to ensure deterministic dumping (though any excess land works)
        to_bottom = sorted(excess_lands, key=lambda c: c.name)
        
        # Only dump excess lands if we have more than 4.
        if len(to_bottom) > 4:
            to_bottom = to_bottom[4:]
        else:
            to_bottom = []
            
        # If we still need to dump cards, dump high CMC, non-land cards.
        remaining_hand = [c for c in hand if c not in to_bottom]
        
        # Sort by CMC descending
        high_cmc = sorted(remaining_hand, key=lambda c: c.cmc, reverse=True)
        
        dump_count = n - len(to_bottom)
        if dump_count > 0:
            to_bottom.extend(high_cmc[:dump_count])
            
        return to_bottom

    def main_phase(self, gs) -> None:
        # 1. Play lands first.
        self._play_land_if_able(gs)
        
        # 2. Prioritize casting the cheapest, most impactful artifacts/spells.
        # Sort by CMC ascending to ensure we play the most efficient cards first.
        castable_cards = sorted(gs.hand(), key=lambda c: c.cmc)
        
        for card in castable_cards:
            # Check if it's an artifact or a low-cost spell we want to leverage.
            is_synergy_card = (card.name in ARTIFACT_STARS or 
                               card.name in ["Metallic Rebuke", "Unholy Heat", "Tamiyo, Inquisitive Student"])
            
            if is_synergy_card and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs) -> None:
        # 3. Cast remaining spells/utility cards.
        
        # Re-sort the hand to ensure we try to cast the cheapest remaining cards first.
        remaining_hand = sorted(gs.hand(), key=lambda c: c.cmc)
        
        for card in remaining_hand:
            # Check if the card is castable and is not a land (lands are handled in main_phase)
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                
    def _play_land_if_able(self, gs):
        """Helper function to play any available land."""
        lands_in_hand = [c for c in gs.hand() if c.is_land()]
        
        # Play the first available land (simplistic approach)
        if lands_in_hand:
            land_to_play = lands_in_hand[0]
            # We assume land costs are always payable if the land is in hand.
            gs.play_land(land_to_play)
            gs._log(f"Played land: {land_to_play.name}")