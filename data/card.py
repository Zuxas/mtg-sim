"""
card.py — Card object model + tag system

Each Card represents one MTG card with structured fields pulled from Scryfall
plus a computed tag set the APL uses for decision-making.
"""

from dataclasses import dataclass, field
from typing import Optional
from typing import Optional


# ---------------------------------------------------------------------------
# Tag constants — add as needed for new archetypes
# ---------------------------------------------------------------------------

class Tag:
    LAND          = "land"
    BASIC_LAND    = "basic_land"
    FETCH_LAND    = "fetch_land"
    CREATURE      = "creature"
    INSTANT       = "instant"
    SORCERY       = "sorcery"
    ARTIFACT      = "artifact"
    ENCHANTMENT   = "enchantment"
    PLANESWALKER  = "planeswalker"

    # Functional roles (archetype-specific, set manually or via oracle text parsing)
    ONE_DROP      = "one_drop"
    TWO_DROP      = "two_drop"
    THREE_DROP    = "three_drop"
    THREAT        = "threat"
    REMOVAL       = "removal"
    CANTRIP       = "cantrip"
    DISCARD       = "discard"
    COUNTER        = "counter"
    RAMP          = "ramp"
    COMBO_PIECE   = "combo_piece"
    ANTHEM        = "anthem"
    LORDS         = "lords"


# ---------------------------------------------------------------------------
# Card dataclass
# ---------------------------------------------------------------------------

@dataclass
class Card:
    # Core identity (from Scryfall)
    name: str
    mana_cost: str                          # e.g. "{1}{W}{W}"
    cmc: float                              # converted mana cost
    type_line: str                          # e.g. "Creature — Human Soldier"
    oracle_text: str = ""
    power: Optional[str] = None            # None for non-creatures
    toughness: Optional[str] = None
    colors: list[str] = field(default_factory=list)   # ["W", "U", "B", "R", "G"]
    color_identity: list[str] = field(default_factory=list)
    scryfall_id: str = ""

    # Computed tags (set by tagger or manually for archetype APLs)
    tags: set[str] = field(default_factory=set)

    # +1/+1 counters (updated by lord ETB triggers)
    counters: int = 0

    # For clone effects — name of the card being copied
    copying: Optional[str] = None

    # --- Permanent state tracking (Phase 0A) ---
    # Summoning sickness — True until controller's next untap step
    summoning_sickness: bool = False
    # Tapped state — lands tap for mana, creatures tap to attack
    tapped: bool = False
    # Which turn this permanent entered the battlefield (0 = not on battlefield)
    turn_entered: int = 0

    def __post_init__(self):
        self._auto_tag()

    def _auto_tag(self):
        """Populate basic tags from type_line and cmc."""
        t = self.type_line.lower()
        if "land" in t:
            self.tags.add(Tag.LAND)
            if "basic" in t:
                self.tags.add(Tag.BASIC_LAND)
        if "creature" in t:
            self.tags.add(Tag.CREATURE)
        if "instant" in t:
            self.tags.add(Tag.INSTANT)
        if "sorcery" in t:
            self.tags.add(Tag.SORCERY)
        if "artifact" in t:
            self.tags.add(Tag.ARTIFACT)
        if "enchantment" in t:
            self.tags.add(Tag.ENCHANTMENT)
        if "planeswalker" in t:
            self.tags.add(Tag.PLANESWALKER)

        # CMC drop tags (non-land only)
        if Tag.LAND not in self.tags:
            if self.cmc <= 1:
                self.tags.add(Tag.ONE_DROP)
            elif self.cmc == 2:
                self.tags.add(Tag.TWO_DROP)
            elif self.cmc == 3:
                self.tags.add(Tag.THREE_DROP)

    def has(self, *tags: str) -> bool:
        """Check if card has all of the given tags."""
        return all(t in self.tags for t in tags)

    def is_land(self) -> bool:
        return Tag.LAND in self.tags

    def is_castable(self, available_mana: int) -> bool:
        """Simplified check — used when no ManaPool available."""
        return self.cmc <= available_mana and not self.is_land()

    def is_castable_with_pool(self, pool) -> bool:
        """
        Full color pip validation against a ManaPool.
        Parses mana cost string e.g. '{2}{W}{U}' and checks pip by pip.
        """
        if self.is_land():
            return False
        return pool.can_pay(self.mana_cost, self.cmc)

    def effective_power(self) -> int:
        """Base power + +1/+1 counters + Lord/static bonuses."""
        lord_bonus = getattr(self, "_lord_power_bonus", 0)
        try:
            return int(self.power or 0) + self.counters + lord_bonus
        except ValueError:
            return self.counters + lord_bonus

    def effective_toughness(self) -> int:
        """Base toughness + +1/+1 counters + Lord/static bonuses."""
        lord_bonus = getattr(self, "_lord_toughness_bonus", 0)
        try:
            return int(self.toughness or 0) + self.counters + lord_bonus
        except ValueError:
            return self.counters + lord_bonus

    def __repr__(self):
        return f"Card({self.name!r}, cmc={self.cmc}, tags={self.tags})"


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    thalia = Card(
        name="Thalia, Guardian of Thraben",
        mana_cost="{1}{W}",
        cmc=2,
        type_line="Legendary Creature — Human Soldier",
        oracle_text="First strike\nNoncreature spells cost {1} more to cast.",
        power="2",
        toughness="1",
        colors=["W"],
    )
    thalia.tags.add(Tag.THREAT)
    thalia.tags.add(Tag.LORDS)

    print(thalia)
    print("Is creature:", thalia.has(Tag.CREATURE))
    print("Is 2-drop:", thalia.has(Tag.TWO_DROP))
    print("Castable with 2 mana:", thalia.is_castable(2))
    print("Castable with 1 mana:", thalia.is_castable(1))
