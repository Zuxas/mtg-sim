"""Mathemagics — {X}{X}{U}{U} Sorcery

Oracle:
  Target player draws 2^X cards. (2^0 = 1, 2^1 = 2, 2^2 = 4, 2^3 = 8,
  2^4 = 16, 2^5 = 32, and so on.)

Decks: Izzet Cauldron, any Standard blue draw engine, Simic Ouroboroid.

Key decisions:
- Variable cost: total mana = X + X + 2 (the {U}{U}). So:
  X=1: cost 4, draw 2 cards.
  X=2: cost 6, draw 4 cards.
  X=3: cost 8, draw 8 cards.
  X=4: cost 10, draw 16 cards.
- Diminishing mana efficiency but exponentially more cards.
- With Lorehold miracle: cast for {2} regardless of CMC = extreme value.
  At X=3 normally costs 8; miracle {2} = 8 cards for {2}.
- With Zaffai (free once per turn): free Mathemagics at X=3 = 8 cards.
- With Prismari storm: cast Mathemagics, storm copies also draw 2^X cards.
  Two prior spells: 3 copies × 8 cards = 24 cards drawn.
- Best X values: X=2 (affordable) or X=3 (with Lorehold/Zaffai).
- Use Zimone (infinite analyst) to reduce X-spell cost further.

Spec: apl/card_specs/mathemagics.py
"""
from __future__ import annotations
import math

NAME = "Mathemagics"
BASE_COLOR_COST = 2  # the {U}{U} portion


def effective_cost(x: int) -> int:
    """Total mana cost for Mathemagics at X.
    Cost = X + X + 2 = 2X + 2.
    """
    return 2 * x + BASE_COLOR_COST


def cards_drawn(x: int) -> int:
    """Cards drawn = 2^X."""
    return 2 ** x


def cast(gs, x_value: int = 2, opponent=None) -> bool:
    """Cast Mathemagics at the given X value.

    Default X=2 (cost 6, draw 4). With Lorehold miracle or Zaffai,
    called via cast_free() instead.
    Returns True if cast.
    """
    cost = effective_cost(x_value)
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.total() >= cost:
            try:
                gs.mana_pool.pay("{" + str(cost) + "}", cost)
            except Exception:
                continue
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            draws = cards_drawn(x_value)
            gs.zones.draw(draws)
            gs._log(f"  Mathemagics X={x_value}: draw {draws} cards (cost {cost})")
            return True
    return False


def cast_free(gs, x_value: int = 3, opponent=None) -> bool:
    """Cast Mathemagics for free (Lorehold miracle / Zaffai).

    Higher X is better when free (X=3 → 8 cards, X=4 → 16 cards).
    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME:
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            draws = cards_drawn(x_value)
            gs.zones.draw(draws)
            gs._log(f"  Mathemagics X={x_value} (FREE): draw {draws} cards")
            return True
    return False


def best_x_for_mana(available_mana: int) -> int:
    """Compute highest X we can cast given available mana.
    cost = 2X + 2. Solve: X = (available - 2) / 2.
    """
    if available_mana < 4:
        return 0
    return (available_mana - BASE_COLOR_COST) // 2
