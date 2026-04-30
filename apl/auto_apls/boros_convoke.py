# Auto-generated APL for Boros Convoke (gemma draft)
# 2026-04-30

from data.card import Card, Tag
from apl.base_apl import BaseAPL

# Core engines and high-value threats for Boros Convoke
CORE_THREATS = {"Knight-Errant of Eos", "Yotian Frontliner", "Gleeful Demolition", "Warden of the Inner Sky"}
HIGH_VALUE_FINISHERS = {"Sanguine Evangelist", "Warleader's Call", "Mirrex"}

class BorosConvokeAPL(BaseAPL):
    name = "Boros Convoke"
    win_condition_damage = 20
    max_turns = 15

    def keep(self, hand: list, mulligans: int, on_play: bool) -> bool:
        """
        Mulligan strategy: Prioritize land count and early board presence.
        """
        lands = [c for c in hand if c.is_land()]
        
        # Must have at least 2 lands to start the board.
        if len(lands) < 2:
            return False
        
        # Must have at least one early threat or utility spell.
        has_threat = any(c.name in CORE_THREATS for c in hand)
        
        if has_threat:
            return True
        
        # If no immediate threat, rely on mulligans or high land count.
        return len(lands) >= 3 and mulligans >= 1

    def bottom(self, hand: list, n: int) -> list:
        """
        Bottom strategy: Dump excess lands and high-cost, non-essential cards.
        """
        # 1. Identify excess lands (keep the best 3-4)
        all_lands = [c for c in hand if c.is_land()]
        # Sort by name to ensure deterministic dumping of excess lands
        excess_lands = all_lands[3:] if len(all_lands) > 3 else []
        
        # 2. Identify high-CMC, non-essential cards to dump
        non_land_cards = [c for c in hand if not c.is_land()]
        
        # Sort by CMC descending, excluding the core threats we want to keep
        high_cmc_to_dump = sorted(
            [c for c in non_land_cards if c.name not in CORE_THREATS and c.name not in HIGH_VALUE_FINISHERS],
            key=lambda c: c.cmc, reverse=True
        )
        
        to_bottom = excess_lands
        
        # Fill remaining slots with high-CMC non-essential cards
        remaining_slots = n - len(to_bottom)
        if remaining_slots > 0:
            to_bottom.extend(high_cmc_to_dump[:remaining_slots])
            
        return to_bottom

    def main_phase(self, gs) -> None:
        """
        Early game phase (Turns 1-3): Play lands and deploy cheapest, most impactful threats.
        """
        # 1. Play all available lands
        land_hand = [c for c in gs.hand() if c.is_land()]
        for land in land_hand:
            if gs.mana_pool.can_cast(land.mana_cost, land.cmc):
                gs.play_land(land)

        # 2. Deploy core threats in order of cost/impact
        # Prioritize low-cost, high-impact creatures
        for card in list(gs.hand()):
            if card.name in CORE_THREATS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs) -> None:
        """
        Mid/Late game phase: Deploy high-value finishers and remaining threats.
        """
        # 1. Attempt to cast high-value finishers first
        for card in list(gs.hand()):
            if card.name in HIGH_VALUE_FINISHERS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

        # 2. Cast all remaining castable threats/creatures
        for card in list(gs.hand()):
            # Check if it's a creature or spell and if we can afford it
            if (card.has(Tag.CREATURE) or card.has(Tag.INSTANT) or card.has(Tag.SORCERY)) and \
               gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)