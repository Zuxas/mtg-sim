"""Consign to Memory — `{U}` instant, replicate `{1}`.

Oracle:
  Counter target triggered ability or colorless spell. Replicate {1}
  (when cast, you may pay {1} additional mana any number of times; copy
  for each replicate cost paid).

Decks using this spec: Jeskai Blink (4), UW Blink (1), Esper Blink (3).

Goldfish viability: DEAD — nothing to counter without opponent. In
matchup play this counters Archon ETB / Pact upkeep / Summoner's Pact
loss / Storm copy / Tron-piece ETB.

Reference impl: apl/jeskai_blink_match.py:526-546 (respond_to_spell
trigger handler).

Spec: harness/specs/2026-04-29-card-specs-framework.md
"""
from __future__ import annotations

NAME = "Consign to Memory"
CMC = 1  # {U}


def cast_counter(gs, opponent, spell, replicate_count: int = 0) -> bool:
    """Counter a triggered ability or colorless spell.

    Goldfish: no-op (returns False without casting).
    Match: APL provides target spell; we counter it for {U} + optional
    replicate copies.

    Args:
      gs: GameState
      opponent: opponent state (None = goldfish, no-op)
      spell: target spell/trigger (None = no target)
      replicate_count: number of additional copies to pay {1} for each

    Returns True if counter cast.
    """
    if opponent is None or spell is None:
        return False  # goldfish-skip / no target

    cost = CMC + replicate_count  # {U} + {1} per replicate
    if gs.mana_pool.total() < cost:
        return False

    for c in list(gs.zones.hand):
        if c.name == NAME:
            try:
                gs.mana_pool.pay("{U}", cost)
            except Exception:
                continue
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            gs._log(f"  Consign to Memory: counter {spell.name}"
                    + (f" (replicate x{replicate_count})" if replicate_count else ""))
            return True
    return False


def should_counter(spell) -> bool:
    """Heuristic: should we counter this triggered ability / colorless spell?

    Targets high-value triggers from the playbook: Archon ETB, Primeval
    Titan ETB, Emrakul cast trigger, Summoner's Pact upkeep, etc.
    """
    if not spell:
        return False
    target_names = {
        "Archon of Cruelty",
        "Primeval Titan",
        "Emrakul, the Promised End",
        "Summoner's Pact",
        "Pact of Negation",  # don't counter our own; for opp's
        "Slogurk, the Overslime",
        "Karn, the Great Creator",
    }
    if getattr(spell, 'name', '') in target_names:
        return True
    spell_cmc = getattr(spell, 'cmc', 0)
    return spell_cmc >= 4  # high-value spells
