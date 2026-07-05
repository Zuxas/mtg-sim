"""
decision_api.py -- B1 prototype (v0): action enumeration + fork for search.

Spec: harness/specs/2026-07-01-b1-legal-action-api.md (Steps 2/3/6 prototype slice).
Vocabulary: docs/action-vocabulary.md (13 kinds; this v0 implements the main-phase
subset: PLAY_LAND, CAST, PASS -- enough to drive a full game through the existing
match loop via apl/search_apl.py).

Design constraints honored:
- apply_action routes through the SAME engine paths APLs use (gs.play_land,
  gs.cast_spell) -- fidelity inherited, never re-derived (spec Step 3).
- fork() is deepcopy-based v0: CORRECT first, fast later (spec Step 6 replaces it).
- Zero imports from apl/ (engine layer stays below the policy layer).
"""
from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Optional

from data.card import Card, Tag


@dataclass(frozen=True)
class Action:
    kind: str                       # 'PLAY_LAND' | 'CAST' | 'PASS'
    card_name: str = ""
    card_ref: object = field(default=None, compare=False, hash=False)

    def __repr__(self):
        return f"Action({self.kind}{',' + self.card_name if self.card_name else ''})"


PASS = Action('PASS')


def legal_main_actions(gs) -> list[Action]:
    """Enumerate main-phase actions legal RIGHT NOW (post tap_lands).

    Legality mirrors the checks the default MatchAPL pilot performs:
    - one land per turn (gs.land_played)
    - castable = nonland, cmc>0, affordable from the current mana pool
    Deduped by card name (casting either copy of a playset is the same choice).
    """
    actions: list[Action] = []
    seen: set = set()
    hand = list(getattr(gs.zones, 'hand', []) or [])

    if not getattr(gs, 'land_played', True):
        for c in hand:
            if c.is_land() and ('L:' + c.name) not in seen:
                seen.add('L:' + c.name)
                actions.append(Action('PLAY_LAND', c.name, c))

    total = gs.mana_pool.total() if getattr(gs, 'mana_pool', None) else 0
    for c in hand:
        if c.is_land():
            continue
        cmc = getattr(c, 'cmc', None)
        if cmc is None or cmc <= 0 or cmc > total:
            continue
        if ('C:' + c.name) in seen:
            continue
        seen.add('C:' + c.name)
        actions.append(Action('CAST', c.name, c))

    actions.append(PASS)
    return actions


def apply_action(gs, action: Action) -> bool:
    """Execute one action through the canonical engine paths. True on success."""
    if action.kind == 'PASS':
        return True
    # re-resolve the card by name in THIS state's hand (action may come from a fork)
    card = next((c for c in gs.zones.hand if c.name == action.card_name), None)
    if card is None:
        return False
    if action.kind == 'PLAY_LAND':
        return bool(gs.play_land(card))
    if action.kind == 'CAST':
        return bool(gs.cast_spell(card))
    return False


def fork(gs, opp, seed=None):
    """v0 fork: deepcopy both seats' views. Correct, slow (~ms); spec Step 6
    replaces with structured copy + per-state RNG. Eval-only in the prototype.

    WP-B4 RNG independence: deepcopy alone would give each child the parent's
    EXACT internal Random state, so every fork would replay identically and forks
    could not diverge. After the copy we OVERWRITE each child's rng with a fresh
    Random object:
      - explicit `seed`   -> two forks with the same seed are byte-identical
                             (deterministic search / reproducibility).
      - derived (seed None) -> each child seeds from ITS OWN parent stream, so the
                             children are independent and diverge only on
                             rng-dependent lines; the fresh object means the
                             parent's own stream is not aliased by the child.
    Fork is search-only (outside the game byte-stream and the 100k re-anchor)."""
    child_gs  = deepcopy(gs)
    child_opp = deepcopy(opp)
    if child_gs is not None:
        gs_seed = seed if seed is not None else (
            gs.rng.randint(0, 2**63 - 1) if getattr(gs, 'rng', None) is not None
            else random.Random().randint(0, 2**63 - 1))
        child_gs.rng = random.Random(gs_seed)
    if child_opp is not None:
        opp_seed = seed if seed is not None else (
            opp.rng.randint(0, 2**63 - 1) if getattr(opp, 'rng', None) is not None
            else random.Random().randint(0, 2**63 - 1))
        child_opp.rng = random.Random(opp_seed)
    return child_gs, child_opp
