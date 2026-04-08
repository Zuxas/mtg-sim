"""
zones.py — Zone manager

Tracks all card zones for a single player:
  Library, Hand, Battlefield, Graveyard, Exile

All zones are plain lists of Card objects.
The library is a mutable list — the APL pops from index 0 (top).
"""

import random
from dataclasses import dataclass, field
from data.card import Card, Tag


@dataclass
class Zones:
    library:     list[Card] = field(default_factory=list)
    hand:        list[Card] = field(default_factory=list)
    battlefield: list[Card] = field(default_factory=list)
    graveyard:   list[Card] = field(default_factory=list)
    exile:       list[Card] = field(default_factory=list)

    # -----------------------------------------------------------------------
    # Library
    # -----------------------------------------------------------------------

    def shuffle(self):
        random.shuffle(self.library)

    def draw(self, n: int = 1) -> list[Card]:
        """Draw n cards from top of library to hand. Returns drawn cards."""
        drawn = []
        for _ in range(n):
            if not self.library:
                break
            card = self.library.pop(0)
            self.hand.append(card)
            drawn.append(card)
        return drawn

    def library_size(self) -> int:
        return len(self.library)

    # -----------------------------------------------------------------------
    # Hand
    # -----------------------------------------------------------------------

    def hand_size(self) -> int:
        return len(self.hand)

    def lands_in_hand(self) -> list[Card]:
        return [c for c in self.hand if c.is_land()]

    def nonlands_in_hand(self) -> list[Card]:
        return [c for c in self.hand if not c.is_land()]

    def cards_in_hand_with_tag(self, *tags: str) -> list[Card]:
        return [c for c in self.hand if c.has(*tags)]

    def remove_from_hand(self, card: Card):
        self.hand.remove(card)

    def bottom_cards(self, cards: list[Card]):
        """Put a list of cards on the bottom of the library (London Mulligan)."""
        for card in cards:
            self.hand.remove(card)
            self.library.append(card)

    # -----------------------------------------------------------------------
    # Battlefield
    # -----------------------------------------------------------------------

    def lands_on_battlefield(self) -> list[Card]:
        return [c for c in self.battlefield if c.is_land()]

    def creatures_on_battlefield(self) -> list[Card]:
        return [c for c in self.battlefield if c.has(Tag.CREATURE)]

    def permanents_with_tag(self, *tags: str) -> list[Card]:
        return [c for c in self.battlefield if c.has(*tags)]

    def play_from_hand(self, card: Card):
        """Move a card from hand to battlefield."""
        self.remove_from_hand(card)
        self.battlefield.append(card)

    def cast_to_graveyard(self, card: Card):
        """Cast a non-permanent (instant/sorcery) — goes to graveyard after resolving."""
        self.remove_from_hand(card)
        self.graveyard.append(card)

    def destroy(self, card: Card):
        self.battlefield.remove(card)
        self.graveyard.append(card)

    def exile_permanent(self, card: Card):
        self.battlefield.remove(card)
        self.exile.append(card)

    # -----------------------------------------------------------------------
    # Utility
    # -----------------------------------------------------------------------

    def count_lands_in_play(self) -> int:
        return len(self.lands_on_battlefield())

    def land_types_in_play(self) -> set[str]:
        """Return set of basic land types on battlefield (Plains, Island, etc.)."""
        types = set()
        for card in self.lands_on_battlefield():
            t = card.type_line.lower()
            for basic in ("plains", "island", "swamp", "mountain", "forest"):
                if basic in t:
                    types.add(basic.capitalize())
        return types

    def __repr__(self):
        return (
            f"Zones(lib={len(self.library)}, hand={len(self.hand)}, "
            f"bf={len(self.battlefield)}, gy={len(self.graveyard)}, "
            f"ex={len(self.exile)})"
        )
