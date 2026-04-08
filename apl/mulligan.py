"""
mulligan.py — London Mulligan logic

London Mulligan rules:
  - Draw 7 cards
  - If you don't want to keep, shuffle back and draw 7 again
  - Each mulligan costs you 1 card bottomed at the end
  - You may mulligan down to 0 cards (though the APL should never go that low)

Each archetype defines its own keep() function.
The generic fallback uses a simple land count heuristic.
"""

import random
import copy
from data.card import Card, Tag
from engine.zones import Zones


# ---------------------------------------------------------------------------
# Generic keep heuristic (fallback if archetype doesn't override)
# ---------------------------------------------------------------------------

def generic_keep(hand: list[Card], mulligans_taken: int, on_play: bool) -> bool:
    """
    Keep if:
      - 2-5 lands in a 7-card hand
      - 2-4 lands in a 6-card hand
      - 2-3 lands in a 5-card hand
      - any 4-card hand or smaller
    """
    lands = sum(1 for c in hand if c.is_land())
    size = len(hand)

    if size <= 4:
        return True
    if size == 5:
        return 2 <= lands <= 3
    if size == 6:
        return 2 <= lands <= 4
    return 2 <= lands <= 5


def generic_bottom(hand: list[Card], n: int) -> list[Card]:
    """
    Choose n cards to bottom after keeping a mulligan hand.
    Default: bottom excess lands first, then highest CMC spells.
    """
    lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.cmc)
    spells = sorted([c for c in hand if not c.is_land()], key=lambda c: -c.cmc)

    to_bottom = []
    land_count = len(lands)

    # Bottom excess lands (keep 2-3)
    target_lands = 2 if land_count > 3 else land_count
    excess_lands = lands[target_lands:]
    to_bottom.extend(excess_lands[:n])

    # Fill remaining with highest CMC spells
    still_needed = n - len(to_bottom)
    to_bottom.extend(spells[:still_needed])

    return to_bottom[:n]


# ---------------------------------------------------------------------------
# Mulligan engine
# ---------------------------------------------------------------------------

def take_opening_hand(
    deck: list[Card],
    keep_fn=None,
    bottom_fn=None,
    on_play: bool = True,
    max_mulligans: int = 4,
    verbose: bool = False,
) -> tuple[list[Card], list[Card], int]:
    """
    Simulate London Mulligan.

    Args:
        deck:           Full shuffled decklist
        keep_fn:        fn(hand, mulligans_taken, on_play) -> bool
        bottom_fn:      fn(hand, n_to_bottom) -> list[Card]
        on_play:        Whether we're on the play
        max_mulligans:  Maximum number of mulligans before forced keep
        verbose:        Print mulligan decisions

    Returns:
        (hand, remaining_library, mulligans_taken)
    """
    keep_fn   = keep_fn   or generic_keep
    bottom_fn = bottom_fn or generic_bottom

    library = list(deck)
    random.shuffle(library)

    mulligans = 0

    while True:
        # Draw 7
        hand    = library[:7]
        library = library[7:]

        hand_size = 7 - mulligans
        is_forced = mulligans >= max_mulligans

        if verbose:
            land_count = sum(1 for c in hand if c.is_land())
            print(f"  Hand {mulligans}: {[c.name for c in hand]} "
                  f"({land_count} lands)")

        if is_forced or keep_fn(hand, mulligans, on_play):
            # Keep — bottom (mulligans) cards
            to_bottom = bottom_fn(hand, mulligans) if mulligans > 0 else []
            for card in to_bottom:
                hand.remove(card)
                library.append(card)

            if verbose:
                bottomed = [c.name for c in to_bottom]
                print(f"  Keep {len(hand)}-card hand"
                      + (f", bottoming: {bottomed}" if bottomed else ""))
            break

        else:
            # Mulligan — return all 7 to library and reshuffle
            library.extend(hand)
            random.shuffle(library)
            mulligans += 1

            if verbose:
                print(f"  Mulligan {mulligans}")

    return hand, library, mulligans
