# Auto-generated APL for Izzet Lessons (gemma draft)
# 2026-04-30

from data.card import Card, Tag
from apl.base_apl import BaseAPL

class IzzetLessonsAPL(BaseAPL):
    AUTO_GENERATED = True  # flagged for rewrite
    name = "Izzet Lessons"
    win_condition_damage = 20
    max_turns = 15

    def keep(self, hand: list, mulligans: int, on_play: bool) -> bool:
        # We need land fixing and a high density of spells to execute the combo.
        lands = [c for c in hand if c.is_land()]
        spells = [c for c in hand if not c.is_land()]

        # Minimum requirement: 2 lands and at least 3 spells.
        if len(lands) < 2 or len(spells) < 3:
            return False

        # If we have too many lands (e.g., 6+), we might be too slow.
        if len(lands) > 5 and mulligans < 2:
            return False

        # If we have few spells, but many mulligans, it might be worth keeping.
        if len(spells) < 3 and mulligans >= 2:
            return True

        return True

    def bottom(self, hand: list, n: int) -> list:
        # 1. Identify excess lands (keep at least 4-5).
        lands = [c for c in hand if c.is_land()]
        excess_lands = lands[4:] if len(lands) > 4 else []

        # 2. Identify spells to dump. Prioritize high CMC, non-synergistic spells.
        spells = [c for c in hand if not c.is_land()]
        
        # Sort by CMC descending to dump the biggest threats first.
        high_cmc_spells = sorted(spells, key=lambda c: c.cmc, reverse=True)

        to_bottom = []
        
        # Dump excess lands first
        for s in excess_lands:
            if len(to_bottom) < n:
                to_bottom.append(s)

        # Dump high CMC spells next
        for s in high_cmc_spells:
            if len(to_bottom) >= n:
                break
            to_bottom.append(s)
            
        return to_bottom[:n]

    def main_phase(self, gs) -> None:
        # 1. Play all available lands first.
        lands_to_play = [c for c in gs.hand() if c.is_land()]
        for card in lands_to_play:
            if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.play_land(card)

        # 2. Cast cheap, high-impact spells (Interaction/Draw)
        # Prioritize Boomerang Basics and It'll Quench Ya!
        
        spells_to_cast = []
        for card in list(gs.hand()):
            if not card.is_land():
                # Check for key interaction/draw spells
                if card.name in ["Boomerang Basics", "It'll Quench Ya!", "Artist's Talent"]:
                    spells_to_cast.append(card)
                # Also cast cheap utility spells if available
                elif card.cmc <= 2 and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    spells_to_cast.append(card)

        for card in spells_to_cast:
            if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs) -> None:
        # 3. Cast all remaining castable spells to maximize value (Storm).
        
        spells_to_cast = []
        for card in list(gs.hand()):
            if not card.is_land():
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    spells_to_cast.append(card)

        # Cast them in order of increasing CMC to ensure we use up mana efficiently.
        spells_to_cast.sort(key=lambda c: c.cmc)
        
        for card in spells_to_cast:
            gs.cast_spell(card)