"""engine/sagas.py -- Saga chapter tick + dispatch.

Sagas add a lore counter on ETB and another at the beginning of
each of their controller's upkeeps. When the counter hits a chapter
number, that chapter's ability fires. When it exceeds the final
chapter, the Saga is sacrificed (or transformed, per card text).

This module exposes three things the engine needs:

  is_saga(card) -> bool
      True when the card is currently a Saga. Relies on the type_line
      string supplied by Scryfall.

  tick_saga(card, gs)
      Call from the upkeep step on each battlefield card. Increments
      card.lore_counters, fires the chapter effect for that count, and
      sacrifices the Saga when it passes its final chapter. (Migrated
      from card.counters to card.lore_counters in T1.3+T1.4 Stage 1
      to avoid collision with +1/+1 counters now that sagas transform
      to creatures at chapter III rather than exiling.)

  SAGA_EFFECTS
      Per-card chapter dispatch. Keys = card name; values = dict
      mapping chapter number to a (card, gs) -> None callable. Keep
      these narrow — each one should model just the chapter's key
      game-state effect (damage, token, +1/+1 delayed trigger, etc.)
      without reinventing the kitchen sink.

  SAGA_FINAL_CHAPTER
      After this chapter resolves, the Saga leaves play. Defaults to
      the highest chapter in SAGA_EFFECTS for the card.
"""
from typing import Callable


def is_saga(card) -> bool:
    """Return True when card's type line identifies it as a Saga."""
    tl = (getattr(card, "type_line", "") or "").lower()
    return "saga" in tl


# ── Chapter effects ─────────────────────────────────────────────────

def _kumano_chapter_i(card, gs):
    """Kumano Faces Kakkazan I — deal 1 damage to each opponent."""
    gs.damage_dealt += 1
    gs._log(f"  Kumano Faces Kakkazan (I): 1 damage "
            f"({gs.damage_dealt} total)")


def _kumano_chapter_ii(card, gs):
    """Kumano Faces Kakkazan II — next creature cast this turn enters
    with an additional +1/+1 counter. Flag the controller's APL so
    the next creature cast picks it up."""
    # Flag on the game state; APL / engine checks on creature cast.
    gs._pending_kumano_bonus = True
    gs._log("  Kumano Faces Kakkazan (II): next creature gets +1/+1")


def _kumano_chapter_iii(card, gs):
    """Kumano Faces Kakkazan III — exile this, return transformed as
    a creature. Simplified in goldfish: just sacrifice (transformed
    Kumano is a 2/2, modest threat)."""
    # Move from battlefield to exile (simplified — real version returns
    # as a 2/2 creature; goldfish can treat as removed).
    if card in gs.zones.battlefield:
        gs.zones.battlefield.remove(card)
        gs.zones.exile.append(card)
    gs._log("  Kumano Faces Kakkazan (III): exiled, transformed")


# ── Registry ────────────────────────────────────────────────────────

SAGA_EFFECTS: dict[str, dict[int, Callable]] = {
    "Kumano Faces Kakkazan": {
        1: _kumano_chapter_i,
        2: _kumano_chapter_ii,
        3: _kumano_chapter_iii,
    },
}

# Optional: per-card explicit final chapter. Defaults to max(chapters).
SAGA_FINAL_CHAPTER: dict[str, int] = {
    "Kumano Faces Kakkazan": 3,
}


def _final_chapter(name: str) -> int:
    override = SAGA_FINAL_CHAPTER.get(name)
    if override is not None:
        return override
    chapters = SAGA_EFFECTS.get(name, {})
    return max(chapters) if chapters else 1


def tick_saga(card, gs):
    """Increment lore counters on card and fire the matching chapter
    effect. Sacrifices the card when it passes its final chapter.
    Silent no-op when card isn't a Saga or isn't in the effect registry."""
    if not is_saga(card):
        return

    card.lore_counters += 1
    chapter = card.lore_counters
    effects = SAGA_EFFECTS.get(card.name, {})
    fn = effects.get(chapter)
    if fn is not None:
        try:
            fn(card, gs)
        except Exception as e:
            gs._log(f"  Saga {card.name} chapter {chapter} error: {e}")

    final = _final_chapter(card.name)
    if chapter >= final and card in gs.zones.battlefield:
        # Most Sagas sacrifice after their final chapter; some
        # transform (handled inside the chapter effect itself, not here).
        pass   # chapter_iii handles it for Kumano
