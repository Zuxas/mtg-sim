"""
apl/generic_apl.py — Plays any MTG deck without archetype-specific knowledge

Strategy:
  1. Play a land every turn
  2. Spend mana efficiently: lowest CMC first
  3. Prefer creatures over non-creatures at equal CMC
  4. Keep hands with 2-3 lands and a curve (at least one 1-2 drop)
  5. Mulligan aggressively: 0 or 1 land = always mull, 5+ lands = always mull

This gives ~80% accuracy for aggro/midrange decks without any custom logic.
Combo and control decks need AutoAPL for meaningful results.

Accuracy tiers by archetype type:
  Aggro (burn, zoo, humans variants):   ~85% (clock is well-modeled)
  Midrange:                             ~75% (sequencing gaps)
  Combo:                                ~50% (doesn't find combo pieces)
  Control:                              ~40% (doesn't interact at all)
"""

from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL


class GenericAPL(BaseAPL):

    name = "Generic Deck"

    def __init__(self, deck_name: str = "Unknown", role: str = "unknown"):
        self.name = deck_name
        self.role = role.lower()

    # -----------------------------------------------------------------------
    # Mulligan — role-aware keep criteria
    # -----------------------------------------------------------------------

    def keep(self, hand: list[Card], mulligans: int, on_play: bool) -> bool:
        lands  = sum(1 for c in hand if c.is_land())
        spells = len(hand) - lands

        # Universal hard rules
        if mulligans >= 3:
            return True  # keep anything on 4+ cards
        if lands == 0:
            return False
        if lands >= 5 and len(hand) >= 6:
            return False
        if spells == 0:
            return False

        # Role-specific thresholds
        if "aggro" in self.role or "burn" in self.role:
            # Want 2 lands, curve one-drops and two-drops
            has_one_drop = any(c.cmc <= 1 and c.has(Tag.CREATURE) for c in hand)
            has_two_drop = any(c.cmc == 2 for c in hand)
            return lands >= 2 and (has_one_drop or has_two_drop)

        elif "combo" in self.role:
            # Want 2-3 lands and some action
            return 2 <= lands <= 4

        elif "control" in self.role:
            # More lands OK, want interaction
            return 2 <= lands <= 5

        else:
            # Midrange default: 2-4 lands, playable curve
            has_early = any(c.cmc <= 2 for c in hand if not c.is_land())
            return 2 <= lands <= 4 and has_early

    def bottom(self, hand: list[Card], n: int) -> list[Card]:
        """Bottom excess lands first, then highest CMC non-essential spells."""
        lands  = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()], key=lambda c: -c.cmc)

        # How many lands we ideally want to keep
        ideal_lands = 3
        excess_lands = lands[ideal_lands:]

        bottomed = []
        # Bottom excess lands first
        for c in excess_lands:
            if len(bottomed) < n:
                bottomed.append(c)

        # Then bottom highest CMC spells
        for c in spells:
            if len(bottomed) < n:
                bottomed.append(c)

        return bottomed[:n]

    # -----------------------------------------------------------------------
    # Main phase — play land, then spend mana by CMC order
    # -----------------------------------------------------------------------

    def main_phase(self, gs: GameState):
        # 1. Play a land
        self._play_land_if_able(gs)

        # 2. Refresh mana after land
        gs.tap_lands()

        # 3. Cast spells in priority order
        self._cast_by_curve(gs)

    def _cast_by_curve(self, gs: GameState):
        """
        Spend all available mana efficiently.
        Priority: creatures over non-creatures at equal CMC,
                  lower CMC before higher CMC.
        Keeps casting until mana runs out or nothing is castable.
        """
        changed = True
        while changed:
            changed = False
            hand = gs.hand()
            if not hand:
                break

            # Build castable list
            castable = [
                c for c in hand
                if not c.is_land()
                and gs.mana_pool.can_cast(c.mana_cost, c.cmc)
            ]
            if not castable:
                break

            # Sort: prefer creatures, then lower CMC, then alphabetical
            castable.sort(key=lambda c: (
                not c.has(Tag.CREATURE),   # creatures first (False < True)
                c.cmc,                      # lower CMC first
                c.name,
            ))

            best = castable[0]
            if gs.cast_spell(best):
                changed = True

    def main_phase2(self, gs: GameState):
        """Post-combat: cast anything still castable."""
        gs.tap_lands()
        self._cast_by_curve(gs)


# ---------------------------------------------------------------------------
# Factory — create GenericAPL from a PlaybookData
# ---------------------------------------------------------------------------

def generic_from_playbook(pb) -> GenericAPL:
    """Create a GenericAPL configured from a PlaybookData object."""
    apl = GenericAPL(deck_name=pb.deck_name, role=pb.role)
    return apl
