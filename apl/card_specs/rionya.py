"""Rionya, Fire Dancer — {3}{R}{R} 3/4 Legendary Creature — Human Shaman

Oracle:
  At the beginning of combat on your turn, create X tokens that are copies
  of another target creature you control, where X is the number of
  noncreature spells you've cast this turn.

Decks: Izzet Cauldron, any Standard red/Izzet combo.

Key decisions:
- Cast T5 (3RR). 3/4 body.
- Combat trigger: create X copies of your best creature, where X = spells
  cast this turn. All copies have haste (standard for token copies at combat).
  e.g. Cast 3 spells → 3 copies of Laelia (3/2 haste attackers) → swing.
  e.g. Cast 3 spells → 3 copies of 5/5 Prismari (15 flying damage).
  e.g. Cast 2 spells → 2 copies of 7/7 Dawning Archaic.
- With Veyran (doubles triggers): combat trigger fires twice = 2X tokens.
- With Prismari (storm): storm copies count as spells for X.
- Best combo: build up spell count early (cantrips, Emeritus prepared bolts,
  storm) then Rionya creates massive token army.
- Tokens are temporary (exiled at end of turn for some versions, or not —
  depends on oracle; standard token copies usually stay unless specified).
  This oracle doesn't say to exile, so tokens persist.

Spec: apl/card_specs/rionya.py
"""
from __future__ import annotations
from data.card import Card, Tag
from engine.match_state import safe_power, safe_toughness

NAME = "Rionya, Fire Dancer"
CMC = 5   # {3}{R}{R}


def cast(gs, opponent=None) -> bool:
    """Cast Rionya T5. Immediately creates tokens at combat.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            gs._log(f"  Rionya: 3/4, begin-combat creates X copies of best creature "
                    f"(X=noncreature spells this turn)")
            return True
    return False


def is_active(gs) -> bool:
    """True if Rionya is on the battlefield."""
    return any(c.name == NAME for c in gs.zones.battlefield)


def fire_combat_trigger(gs, opponent=None) -> int:
    """At beginning of combat, create X token copies of best creature.

    X = noncreature_spells_this_turn.
    Returns number of tokens created.
    """
    if not is_active(gs):
        return 0

    x = getattr(gs, 'noncreature_spells_this_turn', 0)
    if x == 0:
        return 0

    # Find best creature to copy (highest power, not Rionya itself)
    candidates = [c for c in gs.zones.battlefield
                  if c.has(Tag.CREATURE) and not c.is_land()
                  and c.name != NAME]
    if not candidates:
        return 0

    best = max(candidates, key=lambda c: safe_power(c))
    tokens_created = 0

    for _ in range(x):
        token = Card(f"{best.name} Token", best.mana_cost,
                     safe_power(best), best.type_line,
                     oracle_text=getattr(best, 'oracle_text', ''))
        token.power = str(safe_power(best))
        token.toughness = str(safe_toughness(best))
        token.turn_entered = gs.turn
        token.summoning_sickness = False  # copies at combat have haste
        gs.zones.battlefield.append(token)
        tokens_created += 1

    gs._log(f"  Rionya combat: {x} copies of {best.name} "
            f"({safe_power(best)}/{safe_toughness(best)}) = {x * safe_power(best)} power")
    return tokens_created
