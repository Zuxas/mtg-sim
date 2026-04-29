# Auto-generated APL for Landless Belcher (Gemma draft)
# 2026-04-29

from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL

# Key cards for Landless Belcher (Modern)
MANA_ROCKS = {"Sol Ring", "Mana Crypt", "Chrome Mox"}
FINISHER = "Belcher's Breastplate"
LOW_COST_THREATS = {"Lightning Bolt", "Thoughtseize", "Counterspell"}

class BelcherAPL(BaseAPL):
    name = "Landless Belcher"
    win_condition_damage = 25
    max_turns = 10

    def keep(self, hand: list, mulligans: int, on_play: bool) -> bool:
        """
        Mulligan strategy: Prioritize hands with mana rocks and cheap spells.
        Avoid hands that are mostly lands or too slow.
        """
        if not hand:
            return False

        # Count non-land spells and mana rocks
        spells = [c for c in hand if not c.is_land()]
        mana_rocks_count = sum(1 for c in hand if c.name in MANA_ROCKS)

        # If we have 3+ spells/rocks, we are likely okay.
        if len(spells) >= 3:
            return True

        # If we have 0 spells but 2+ mana rocks, we might be able to ramp into a finish.
        if len(spells) < 3 and mana_rocks_count >= 2:
            return True

        # If we are on the first mulligan and have a decent hand, keep it.
        if mulligans > 0 and len(spells) >= 2:
            return True

        # Otherwise, mulligan.
        return False

    def bottom(self, hand: list, n: int) -> list:
        """
        Bottom strategy: Get the worst lands and high-CMC, non-essential spells to the bottom.
        """
        lands = [c for c in hand if c.is_land()]
        spells = [c for c in hand if not c.is_land()]

        # 1. Prioritize bottoming lands first, as we are landless.
        to_bottom = lands[:]

        # 2. If we still need to bottom cards, take the highest CMC spells that aren't critical.
        # We sort by CMC descending, and take the top N-len(lands) cards.
        remaining_needed = n - len(to_bottom)
        if remaining_needed > 0 and spells:
            # Sort by CMC descending, then alphabetically (to ensure deterministic choice)
            high_cmc_spells = sorted(spells, key=lambda c: (-c.cmc, c.name))
            to_bottom.extend(high_cmc_spells[:remaining_needed])

        return to_bottom[:n]

    def main_phase(self, gs: GameState) -> None:
        """
        Early game phase (Turns 1-3): Play mana rocks and cheap interaction/threats.
        """
        # 1. Play all available mana rocks first.
        rocks_to_play = [c for c in gs.hand() if c.name in MANA_ROCKS and c.is_land() == False]
        for rock in rocks_to_play:
            if gs.mana_pool.cancast(rock.mana_cost, rock.cmc):
                gs.cast_spell(rock)

        # 2. Play cheap interaction/threats (e.g., Lightning Bolt, Thoughtseize).
        # Sort by CMC ascending to maximize early impact.
        threats_and_interaction = sorted([c for c in gs.hand() if c.name in LOW_COST_THREATS],
                                       key=lambda c: c.cmc)

        for card in threats_and_interaction:
            if gs.mana_pool.cancast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs: GameState) -> None:
        """
        Mid/Late game phase: Cast the finisher or remaining threats.
        """
        # 1. Attempt to cast the finisher if it's in hand and affordable.
        if any(c.name == FINISHER for c in gs.hand()):
            finisher = next((c for c in gs.hand() if c.name == FINISHER), None)
            if finisher and gs.mana_pool.cancast(finisher.mana_cost, finisher.cmc):
                gs.cast_spell(finisher)
                return # Finisher is the priority

        # 2. If the finisher isn't ready, cast any remaining threats or high-impact spells.
        remaining_spells = sorted([c for c in gs.hand() if c.name not in MANA_ROCKS and c.name != FINISHER],
                               key=lambda c: c.cmc)

        for card in remaining_spells:
            if gs.mana_pool.cancast(card.mana_cost, card.cmc):
                gs.cast_spell(card)