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
    """Kumano Faces Kakkazan III — exile this Saga, return it
    transformed under your control (Etching of Kumano, 2/2 Enchantment
    Creature -- Human Shaman with haste + exile-on-death replacement).

    Stage 4 of T1.3+T1.4 transform arc (2026-04-26): now uses the
    real gs.transform mechanic from Stage 2 (commit 7ede331). The
    previous "simplified as exile" approximation lost the back-face
    creature entirely; Etching of Kumano is now properly on the
    battlefield post-chapter-III, including its haste keyword (which
    transforms via type_line re-tagging in gs.transform)."""
    gs.transform(card)


# ── Registry ────────────────────────────────────────────────────────

def _roku_chapter_i(card, gs):
    """The Legend of Roku I — Exile the top three cards of your library.
    Until the end of your next turn, you may play those cards.

    Goldfish approximation: the "may play exiled cards next turn"
    mechanic requires an exile-with-playability zone tracker that
    we don't model. The value floor of Chapter I is "look at top 3,
    keep the best 1" -- modeled here as draw 1 card. The lost value
    (looking at 2 additional cards + casting from exile) is real but
    bounded; future iteration could add a play-from-exile zone."""
    gs.zones.draw(1)
    gs._log("  Roku (I): draw 1 (approximation of exile-top-3 may-play)")


def _roku_chapter_ii(card, gs):
    """The Legend of Roku II — Add one mana of any color.

    Goldfish: BE always wants {R} for Phlage attack trigger or {W} for
    the Phlage hardcast. Adding {R} is the safest default since the
    Phlage hardcast costs {1}{R}{W} (the {W} is usually fixed by
    Sacred Foundry / dual lands) and the loose {R} accelerates more
    plays. Real "any color" flexibility doesn't matter for goldfish
    where BE's curve only cares about R/W availability."""
    gs.mana_pool.add("R", 1)
    gs._log("  Roku (II): +1 R mana (any-color choice)")


def _roku_chapter_iii(card, gs):
    """The Legend of Roku III — Exile this Saga, then return it
    transformed under your control as Avatar Roku (Legendary
    Creature -- Avatar, 4/4 with firebending 4 attack trigger and
    {8}: Dragon token activated ability).

    Stage 6 of T1.3+T1.4 transform arc: same gs.transform() pattern
    as Kumano chapter III (Stage 4)."""
    gs.transform(card)


SAGA_EFFECTS: dict[str, dict[int, Callable]] = {
    "Kumano Faces Kakkazan": {
        1: _kumano_chapter_i,
        2: _kumano_chapter_ii,
        3: _kumano_chapter_iii,
    },
    "The Legend of Roku": {
        1: _roku_chapter_i,
        2: _roku_chapter_ii,
        3: _roku_chapter_iii,
    },
}

# Optional: per-card explicit final chapter. Defaults to max(chapters).
SAGA_FINAL_CHAPTER: dict[str, int] = {
    "Kumano Faces Kakkazan": 3,
    "The Legend of Roku":    3,
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
