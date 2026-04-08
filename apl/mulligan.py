"""
mulligan.py — London Mulligan logic

London Mulligan rules:
  - Draw 7 cards
  - If you don't want to keep, shuffle back and draw 7 again
  - Each mulligan costs you 1 card bottomed at the end
  - You may mulligan down to 0 cards (though the APL should never go that low)

Each archetype defines its own keep() and optionally keep_vs() functions.
The generic fallback uses a simple land count heuristic.
"""

import random, copy, inspect
from data.card import Card, Tag
from engine.zones import Zones


def generic_keep(hand: list[Card], mulligans_taken: int, on_play: bool) -> bool:
    lands = sum(1 for c in hand if c.is_land())
    size  = len(hand)
    if size <= 4: return True
    if size == 5: return 2 <= lands <= 3
    if size == 6: return 2 <= lands <= 4
    return 2 <= lands <= 5


def generic_bottom(hand: list[Card], n: int) -> list[Card]:
    lands  = sorted([c for c in hand if c.is_land()],     key=lambda c: c.cmc)
    spells = sorted([c for c in hand if not c.is_land()], key=lambda c: -c.cmc)
    to_bottom = []
    target_lands = 2 if len(lands) > 3 else len(lands)
    to_bottom.extend(lands[target_lands:][:n])
    still = n - len(to_bottom)
    to_bottom.extend(spells[:still])
    return to_bottom[:n]


def take_opening_hand(
    deck:           list[Card],
    keep_fn=None,
    bottom_fn=None,
    on_play:        bool = True,
    max_mulligans:  int  = 4,
    verbose:        bool = False,
    opp_archetype:  str  = "",
) -> tuple[list[Card], list[Card], int]:
    """
    Simulate London Mulligan.

    keep_fn may be either:
      keep(hand, mulligans, on_play)                 — standard
      keep_vs(hand, mulligans, on_play, opp_arch)    — opponent-aware

    opp_archetype is passed to keep_vs() when the APL supports it,
    enabling deck-specific mulligan logic vs specific opponents.

    Returns (hand, remaining_library, mulligans_taken).
    """
    keep_fn   = keep_fn   or generic_keep
    bottom_fn = bottom_fn or generic_bottom

    # Detect whether keep_fn accepts an opp_archetype 4th argument
    try:
        sig = inspect.signature(keep_fn)
        supports_opp = len(sig.parameters) >= 4
    except Exception:
        supports_opp = False

    library = list(deck)
    random.shuffle(library)
    mulligans = 0

    while True:
        hand    = library[:7]
        library = library[7:]
        is_forced = mulligans >= max_mulligans

        if verbose:
            lc = sum(1 for c in hand if c.is_land())
            print(f"  Hand {mulligans}: {[c.name for c in hand]} ({lc} lands)")

        if is_forced:
            do_keep = True
        elif supports_opp and opp_archetype:
            do_keep = keep_fn(hand, mulligans, on_play, opp_archetype)
        else:
            do_keep = keep_fn(hand, mulligans, on_play)

        if do_keep:
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
            library.extend(hand)
            random.shuffle(library)
            mulligans += 1
            if verbose:
                print(f"  Mulligan {mulligans}")

    return hand, library, mulligans
