# Auto-generated APL for Mono Green Landfall (gemma draft)
# 2026-04-30

from data.card import Card, Tag
from apl.base_apl import BaseAPL

class MonoGreenLandfallAPL(BaseAPL):
    AUTO_GENERATED = True  # flagged for rewrite
    name = "Mono Green Landfall"
    win_condition_damage = 20
    max_turns = 15

    def keep(self, hand: list, mulligans: int, on_play: bool) -> bool:
        # We need enough lands to establish a board presence and ramp.
        lands = [c for c in hand if c.is_land()]
        
        # Minimum requirement: At least 3 lands and some early ramp/utility.
        if len(lands) < 3:
            return False

        # Check for key ramp/utility pieces
        ramp_pieces = ["Llanowar Elves", "Badgermole Cub", "Icetill Explorer"]
        has_ramp = any(c.name in ramp_pieces for c in hand)

        # If we have lots of lands, we can afford to keep a slightly weaker hand.
        if len(lands) >= 5:
            return True
        
        # Otherwise, we must have at least one ramp piece.
        return has_ramp

    def bottom(self, hand: list, n: int) -> list:
        # 1. Identify excess lands (we only want 3-4 lands in the initial hand).
        lands = [c for c in hand if c.is_land()]
        excess_lands = lands[3:] if len(lands) > 3 else []

        # 2. Identify high-cost, non-land spells that aren't critical for the combo.
        # We prioritize keeping the 1-drops and utility spells.
        non_land_spells = [c for c in hand if not c.is_land()]
        
        # Sort by CMC descending, excluding the crucial 1-drops.
        high_cmc_to_discard = sorted(
            [c for c in non_land_spells if c.cmc > 2 and c.name not in ["Llanowar Elves", "Badgermole Cub", "Icetill Explorer"]],
            key=lambda c: c.cmc, reverse=True
        )

        to_bottom = excess_lands + high_cmc_to_discard
        return to_bottom[:n]

    def main_phase(self, gs) -> None:
        # Priority 1: Play all available lands.
        lands_to_play = [c for c in gs.hand() if c.is_land()]
        for land in lands_to_play:
            if gs.mana_pool.can_cast(land.mana_cost, land.cmc):
                gs.play_land(land)

        # Priority 2: Cast 1-drop ramp creatures.
        ramp_creatures = ["Llanowar Elves", "Badgermole Cub"]
        for card in list(gs.hand()):
            if card.name in ramp_creatures and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

        # Priority 3: Cast utility/early threats (Icetill Explorer, Sazh's Chocobo).
        utility_threats = ["Icetill Explorer", "Sazh's Chocobo"]
        for card in list(gs.hand()):
            if card.name in utility_threats and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs) -> None:
        # Try to cast the next most impactful spells/creatures if mana allows.
        
        # Check for mid-cost threats/enchantments
        mid_cost_threats = ["Earthbender Ascension", "Mightform Harmonizer"]
        for card in list(gs.hand()):
            if card.name in mid_cost_threats and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
        
        # Check for remaining utility/combo pieces
        remaining_spells = ["Escape Tunnel", "Esper Origins", "Promising Vein", "Sapling Nursery"]
        for card in list(gs.hand()):
            if card.name in remaining_spells and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                # Only cast if it's not a land (lands are handled in main_phase)
                if not card.is_land():
                    gs.cast_spell(card)