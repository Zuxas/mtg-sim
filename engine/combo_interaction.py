"""
engine/combo_interaction.py -- the shared combo-interaction layer (spec
harness/specs/2026-06-30-modern-combo-interaction.md, Component 1).

PURPOSE
    A single seam where, at a combo opponent's DECISIVE step, OUR specific
    answers (a counter on the combo spell, removal on the lone reanimated body,
    graveyard hate, proactive discard) get a chance to fire. No such seam exists
    on the run_match gauntlet path today (declare_blockers / respond_to_spell /
    combat_trick are never called there -- see the spec "spine" section).

THE NO-REGRESSION CRUX -- this layer is DOUBLE-GATED and inert by default:
    1. Initiation gate (STRUCTURAL): offer_interaction() is reached ONLY from
       inside a combo APL's assembly code at its decisive step. A non-combo
       seat-B APL never calls it, so a non-combo matchup never imports or runs
       this module. Byte-identical BY CONSTRUCTION, not by diffing.
    2. Capability gate (FLAG): offer_interaction() early-returns a no-op result
       unless the opposing (our) APL sets WANTS_COMBO_INTERACTION = True. So even
       when a combo APL IS seat B, if our deck has not opted in, the combo
       proceeds EXACTLY as its un-answered baseline (the honest floor). Mirrors
       the established WANTS_PRIORITY_STACK / WANTS_WARP / WANTS_STORM convention.

    >> SPINE INCREMENT STATUS: NO combo APL calls offer_interaction yet, and NO
    >> APL sets WANTS_COMBO_INTERACTION = True. This module is therefore PURE
    >> INFRASTRUCTURE with ZERO behavioral effect on any matchup. Per-deck
    >> assembly (Component 3) wires the callers + flips the opt-in later.

ZONE-MOVE DISCIPLINE
    When (eventually) an answer is applied, it MUTATES THE SHARED ALIASED ZONE
    LISTS (combo_gs.zones.hand/battlefield/graveyard), because zone moves
    propagate to the underlying TwoPlayerGameState (spec spine #2). SCALAR life
    writes do NOT propagate -- this layer never touches life directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


# Event kinds the combo APL can raise at its decisive step.
COUNTER_WINDOW = "counter_window"   # a combo spell is about to resolve
REANIMATE      = "reanimate"        # a body is about to be reanimated / relied on
GY_SETUP       = "gy_setup"         # the step depends on specific GY contents
RESOLVE_THREAT = "resolve_threat"   # an assembled body is about to win
DISCARD        = "discard"          # proactive hand-disruption checkpoint

_VALID_KINDS = {COUNTER_WINDOW, REANIMATE, GY_SETUP, RESOLVE_THREAT, DISCARD}


@dataclass
class ComboEvent:
    """A checkpoint raised by a combo APL at its decisive step."""
    kind: str                                  # one of the _VALID_KINDS strings
    spell: Optional[Any] = None                # the combo spell (counter_window), else None
    targets: List[Any] = field(default_factory=list)   # bodies entering / relied on
    gy_cards: List[Any] = field(default_factory=list)   # GY contents the step depends on
    meta: dict = field(default_factory=dict)   # free-form, e.g. {"protected": True}


@dataclass
class InteractionResult:
    """Outcome of offer_interaction(). disrupted=True iff the step was answered."""
    disrupted: bool
    detail: str = ""


def offer_interaction(combo_gs, combo_apl, opp_gs, opp_apl, event) -> InteractionResult:
    """Offer OUR APL (opp_apl) a chance to answer the combo APL's decisive step.

    Returns an InteractionResult. disrupted=False (a pure no-op that mutates
    NOTHING) whenever the capability gate is off or our APL passes -- this is the
    inert path the no-regression proof relies on.
    """
    # --- Capability gate (FLAG). Off => inert no-op, nothing inspected/mutated.
    if not getattr(opp_apl, "WANTS_COMBO_INTERACTION", False):
        return InteractionResult(False, "no-interaction-opt-in")

    # Ask our APL for an answer. Contract: a tuple whose [0] is the action verb
    # ("counter" | "remove" | "gy_hate" | "discard"), [1] the answer card in our
    # hand, and an optional [2] target; or None / falsy to pass.
    answer = None
    try:
        answer = opp_apl.answer_combo(opp_gs, combo_gs, event)
    except Exception:
        # An APL-side error must never crash the match path; treat as a pass.
        return InteractionResult(False, "answer-error")
    if not answer:
        return InteractionResult(False, "passed")

    verb = answer[0]
    card = answer[1] if len(answer) > 1 else None
    target = answer[2] if len(answer) > 2 else None

    # --- Apply the answer to the SHARED aliased zone lists (zone moves
    #     propagate; spec spine #2). Pay the answer's cost out of our mana pool
    #     and move our answer card hand -> graveyard (or exile). Each branch is
    #     defensive: a missing target / card is a pass, never a crash.
    applied, detail = _apply_answer(combo_gs, opp_gs, verb, card, target, event)
    if not applied:
        return InteractionResult(False, detail)
    return InteractionResult(True, detail)


def _move(card, src: list, dst: list) -> bool:
    """Identity-safe single-card zone move. Returns True iff it moved."""
    if card is None:
        return False
    for i, c in enumerate(src):
        if c is card:
            dst.append(src.pop(i))
            return True
    return False


def _spend_our_card(opp_gs, card, exile: bool = False) -> None:
    """Move our answer card out of hand; pay its mana if a pool is present."""
    try:
        mc = getattr(card, "mana_cost", None)
        cmc = getattr(card, "cmc", 0)
        pool = getattr(opp_gs, "mana_pool", None)
        if pool is not None and mc is not None and pool.can_cast(mc, cmc):
            pool.pay(mc, cmc)
    except Exception:
        pass
    dst = getattr(opp_gs.zones, "exile", None) if exile else opp_gs.zones.graveyard
    if dst is None:
        dst = opp_gs.zones.graveyard
    _move(card, opp_gs.zones.hand, dst)


def _apply_answer(combo_gs, opp_gs, verb, card, target, event):
    """Resolve one answer verb against the shared combo zones. (Reachable only
    when a combo APL has wired offer_interaction AND we opted in -- not this
    increment.)"""
    cz = combo_gs.zones

    if verb == "counter":
        spell = event.spell
        if spell is None:
            return False, "counter-no-spell"
        # Move the combo spell to its owner's graveyard; the step aborts.
        moved = _move(spell, getattr(cz, "stack", []) or [], cz.graveyard) \
            or _move(spell, cz.hand, cz.graveyard)
        if not moved:
            return False, "counter-spell-not-found"
        _spend_our_card(opp_gs, card)
        return True, "countered"

    if verb == "remove":
        if target is None:
            return False, "remove-no-target"
        exile = bool(card is not None and getattr(opp_gs, "_match_exile_name", None)
                     in ())  # placeholder; per-APL decides exile vs destroy
        dst = cz.graveyard
        if not _move(target, cz.battlefield, dst):
            return False, "remove-target-gone"
        _spend_our_card(opp_gs, card)
        return True, "removed"

    if verb == "gy_hate":
        # Exile the GY cards the step depends on (deny reanimation fuel).
        ex = getattr(cz, "exile", None)
        n = 0
        for gc in list(event.gy_cards) or list(cz.graveyard):
            if _move(gc, cz.graveyard, ex if ex is not None else cz.graveyard):
                n += 1
        if n == 0:
            return False, "gy_hate-empty"
        _spend_our_card(opp_gs, card)
        return True, f"gy_hate-{n}"

    if verb == "discard":
        piece = target
        if piece is None:
            return False, "discard-no-target"
        if not _move(piece, cz.hand, cz.graveyard):
            return False, "discard-piece-gone"
        _spend_our_card(opp_gs, card)
        return True, "discarded"

    return False, f"unknown-verb-{verb}"


class AnswerComboMixin:
    """Mix into an interaction-capable MatchAPL to give it answer_combo().

    Reusable across our interaction decks. Inert until the subclass also sets
    WANTS_COMBO_INTERACTION = True (the capability gate in offer_interaction).
    """

    # Capability gate, OFF by default. A subclass flips it True to opt in.
    WANTS_COMBO_INTERACTION = False

    def answer_combo(self, my_gs, combo_gs, event):
        """Inspect MY hand + mana and return an answer for `event`, or None.

        Answer form: (verb, card[, target]) where verb is
        "counter" | "remove" | "gy_hate" | "discard". Returning None passes.

        General implementation keyed off event.kind; per-deck subclasses may
        override. NOTE: not reached in the spine increment (gate is off
        everywhere), so this is generality scaffolding, not live behavior.
        """
        kind = getattr(event, "kind", None)
        hand = list(getattr(my_gs.zones, "hand", []))
        pool = getattr(my_gs, "mana_pool", None)

        def affordable(c):
            try:
                return pool is not None and pool.can_cast(
                    getattr(c, "mana_cost", None), getattr(c, "cmc", 0))
            except Exception:
                return False

        removal = getattr(self, "MATCH_REMOVAL", {})
        exile_set = getattr(self, "MATCH_EXILE", set())

        if kind == COUNTER_WINDOW:
            # No maindeck counters in a Boros G1 shell; generic hook for SB games.
            for c in hand:
                spec = removal.get(c.name)
                if spec and c.name in ("Annul",) and affordable(c):
                    return ("counter", c)
            return None

        if kind in (RESOLVE_THREAT, REANIMATE):
            target = event.targets[0] if event.targets else None
            if target is None:
                return None
            from engine.match_state import safe_toughness
            tgh = safe_toughness(target)
            # Prefer exile-removal for bodies our damage cannot kill.
            for c in hand:
                spec = removal.get(c.name)
                if not spec or not affordable(c):
                    continue
                _cost, max_tgh = spec
                kills = (max_tgh is None) or (tgh <= max_tgh)
                if kills:
                    return ("remove", c, target)
            return None

        if kind == GY_SETUP:
            GY_HATE = {"Leyline of the Void", "Relic of Progenitus",
                       "Endurance", "Bojuka Bog", "Soul-Guide Lantern"}
            for c in hand:
                if c.name in GY_HATE and (affordable(c) or c.is_land()):
                    return ("gy_hate", c)
            return None

        if kind == DISCARD:
            DISCARD_SPELLS = {"Thoughtseize", "Inquisition of Kozilek", "Duress"}
            piece = event.targets[0] if event.targets else None
            for c in hand:
                if c.name in DISCARD_SPELLS and affordable(c) and piece is not None:
                    return ("discard", c, piece)
            return None

        return None
