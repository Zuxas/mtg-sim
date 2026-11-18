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


BAD_BOTTOMS = 0   # times a bottom() choice had to be corrected (#14)


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
    rng=None,
    shuffle_first:  bool = True,
) -> tuple[list[Card], list[Card], int]:
    """
    Simulate London Mulligan.

    keep_fn may be either:
      keep(hand, mulligans, on_play)                 — standard
      keep_vs(hand, mulligans, on_play, opp_arch)    — opponent-aware

    opp_archetype is passed to keep_vs() when the APL supports it,
    enabling deck-specific mulligan logic vs specific opponents.

    rng: random.Random to shuffle with (default: the global `random`). The
    match engines pass their per-game rng so a seed reproduces the game.
    shuffle_first=False keeps `deck` in the order given: the match engines
    hand over a library that is already shuffled.

    The kept hand always has 7 - mulligans cards (#14): if bottom_fn returns
    too few cards, or one that is not in the hand, the hand is trimmed from
    the end.

    Returns (hand, remaining_library, mulligans_taken).
    """
    rng = rng or random
    keep_fn   = keep_fn   or generic_keep
    bottom_fn = bottom_fn or generic_bottom

    # Detect whether keep_fn accepts an opp_archetype 4th argument
    try:
        sig = inspect.signature(keep_fn)
        supports_opp = len(sig.parameters) >= 4
    except Exception:
        supports_opp = False

    library = list(deck)
    if shuffle_first:
        rng.shuffle(library)
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
            for card in to_bottom[:mulligans]:
                if card in hand:
                    hand.remove(card)
                    library.append(card)
            target = max(0, 7 - mulligans)
            if len(hand) > target:
                # bottom_fn returned too few cards, or cards not in the hand
                msg = (f"bottom() left {len(hand)} cards after {mulligans} mulligan(s), "
                       f"expected {target}; trimming from the end of the hand")
                import os
                if os.environ.get("SIM_DEBUG"):
                    raise ValueError(msg)
                global BAD_BOTTOMS
                BAD_BOTTOMS += 1
                if BAD_BOTTOMS == 1:
                    print(f"  [!MULLIGAN] {msg} (reported once; SIM_DEBUG=1 to raise)")
            while len(hand) > target:
                library.append(hand.pop())
            if verbose:
                bottomed = [c.name for c in to_bottom]
                print(f"  Keep {len(hand)}-card hand"
                      + (f", bottoming: {bottomed}" if bottomed else ""))
            break
        else:
            library.extend(hand)
            rng.shuffle(library)
            mulligans += 1
            if verbose:
                print(f"  Mulligan {mulligans}")

    return hand, library, mulligans
