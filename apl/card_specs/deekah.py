"""Deekah, Fractal Theorist — {4}{U} 3/3 Legendary Creature — Human Wizard

Oracle:
  Magecraft — Whenever you cast or copy an instant or sorcery spell,
  create a 0/0 green and blue Fractal creature token. Put X +1/+1 counters
  on it, where X is the number of instant and sorcery spells you've cast
  this turn.

Decks: Izzet Cauldron, Simic Ouroboroid, any spells deck.

Key decisions:
- Cast T5 (4U). Immediately starts generating tokens.
- Magecraft: first spell = 1/1 Fractal. Second = 2/2. Third = 3/3.
  In burst turn: 3 spells = 3/3 + 2/2 + 1/1 = 6 power of tokens.
- With Veyran (trigger doubles): each spell makes 2 Fractals instead of 1,
  first spell makes two 1/1s, second makes two 2/2s, etc.
- Fractals attack as a swarm or protect Deekah.
- Best synergy: pair with Prismari (storm = many copies = many tokens)
  or Silverquill (casualty creatures made from Fractals).

Spec: apl/card_specs/deekah.py
"""
from __future__ import annotations
from data.card import Card, Tag

NAME = "Deekah, Fractal Theorist"
CMC = 5  # {4}{U}


def cast(gs, opponent=None) -> bool:
    """Cast Deekah T5. Starts generating Fractal tokens immediately.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            gs._log(f"  Deekah: 3/3, magecraft creates X/X Fractal (X=spells cast this turn)")
            return True
    return False


def is_active(gs) -> bool:
    """True if Deekah is on the battlefield."""
    return any(c.name == NAME for c in gs.zones.battlefield)


def create_fractal_token(gs, spells_cast_this_turn: int = None) -> int:
    """Create a Fractal token with X +1/+1 counters.

    X = number of instants/sorceries cast this turn (including this one).
    Returns the X value (token size).
    """
    if not is_active(gs):
        return 0

    if spells_cast_this_turn is None:
        spells_cast_this_turn = getattr(gs, 'noncreature_spells_this_turn', 1)

    x = max(1, spells_cast_this_turn)
    token = Card("Fractal Token", "{0}", x, "Token Creature — Fractal",
                 oracle_text="")
    token.power = str(x)
    token.toughness = str(x)
    token.turn_entered = gs.turn
    token.summoning_sickness = True
    token.counters = x
    gs.zones.battlefield.append(token)
    gs._log(f"  Deekah magecraft: {x}/{x} Fractal token "
            f"(spell #{spells_cast_this_turn} this turn)")
    return x


def total_fractal_power(gs) -> int:
    """Total power of all Fractal tokens on the battlefield."""
    return sum(int(c.power) for c in gs.zones.battlefield
               if c.has(Tag.CREATURE) and 'Fractal' in (getattr(c, 'type_line', '') or ''))
