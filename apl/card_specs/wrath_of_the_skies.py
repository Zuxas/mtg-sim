"""Wrath of the Skies — `{X}{W}{W}` sorcery, energy-based wipe.

Oracle:
  As you cast Wrath of the Skies, get X energy ({E}). You may pay any
  amount of energy you have; destroy each artifact, creature, and
  enchantment with mana value less than or equal to that amount.

Decks using this spec: Jeskai Blink (1 main + 2 sb), Boros Energy
sideboard (3), UW Blink sideboard.

Goldfish viability: DEAD — nothing to destroy. Pitch fodder for March
of Otherworldly Light only.

Reference impl: apl/jeskai_blink_match.py:309-331 (cast logic),
                apl/jeskai_blink_match.py:564-584 (_should_wrath
                heuristic).

Spec: harness/specs/2026-04-29-card-specs-framework.md
"""
from __future__ import annotations

NAME = "Wrath of the Skies"
BASE_CMC = 2  # {W}{W} before X


def cast(gs, opponent=None, x_value: int = 1) -> bool:
    """Cast Wrath. Pays {X}{W}{W}, gets X energy, spends energy to destroy.

    Goldfish: no-op (no targets to destroy).
    Match: x_value chosen by caller based on opp's curve.

    Returns True if cast.
    """
    if opponent is None:
        return False  # goldfish-skip

    cost = BASE_CMC + x_value
    if gs.mana_pool.total() < cost:
        return False

    for c in list(gs.zones.hand):
        if c.name == NAME:
            try:
                gs.mana_pool.pay("{W}{W}", cost)  # engine may approximate X
            except Exception:
                continue
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)

            # Get X energy + spend it to destroy MV <= X creatures (both sides)
            energy_to_spend = x_value
            from data.card import Tag
            killed = 0
            for owner in (opponent, gs):
                for cr in list(owner.zones.battlefield):
                    if cr.has(Tag.CREATURE) and not cr.is_land():
                        if getattr(cr, 'cmc', 99) <= energy_to_spend:
                            owner.zones.battlefield.remove(cr)
                            owner.zones.graveyard.append(cr)
                            killed += 1
            gs._log(f"  Wrath of the Skies X={x_value}: destroyed {killed} creatures")
            return True
    return False


def should_cast(gs, opponent) -> bool:
    """Heuristic: should we cast Wrath?

    Playbook: cast when behind on board (opp creatures >= ours + 2) or
    against single huge threat we can't answer.
    """
    if opponent is None:
        return False
    from data.card import Tag
    from engine.match_state import safe_power
    our = sum(1 for c in gs.zones.battlefield
              if c.has(Tag.CREATURE) and not c.is_land())
    theirs = sum(1 for c in opponent.zones.battlefield
                 if c.has(Tag.CREATURE) and not c.is_land())
    if theirs >= our + 2:
        return True
    big_threats = [c for c in opponent.zones.battlefield
                   if c.has(Tag.CREATURE) and safe_power(c) >= 5]
    if big_threats and our <= 1:
        return True
    return False
