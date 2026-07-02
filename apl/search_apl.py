"""
search_apl.py -- SearchAPL: a deck-agnostic pilot that CHOOSES its plays by
enumerating legal actions and evaluating forked futures (1-ply lookahead),
instead of following hand-written play lines.

This is the Stockfish-prototype seam: replace _choose() with ISMCTS later and
nothing else changes. Spec: 2026-07-01-b1-legal-action-api.md; vocabulary:
docs/action-vocabulary.md.

HONEST SCOPE (v0):
- Searches main-phase 1 sequencing (land choice + cast order) via fork+greedy
  completion + terminal evaluation.
- Combat, priority responses, mulligans: inherits MatchAPL's real-Magic
  heuristics (same defaults every stub APL gets) -- NOT searched yet.
- No hidden-info modeling: evaluates only its own seat's visible outcome
  (board delta, damage, cards kept), never peeks at opponent's hand.
"""
from __future__ import annotations

from data.card import Card, Tag
from apl.match_apl import MatchAPL
from engine.decision_api import legal_main_actions, apply_action, fork, Action, PASS

_MAX_DECISIONS_PER_TURN = 24
_BEAM = 4          # candidate first-actions evaluated by fork each decision
_KW_BONUS = 1.5    # per combat-relevant keyword



def _num(x, default=0) -> float:
    """Oracle data ships power/toughness/cmc as str sometimes ('2', '*', '1+*')."""
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return float(default)

def _board_power(gs) -> float:
    tot = 0.0
    for c in getattr(gs.zones, 'battlefield', []) or []:
        if c.has(Tag.CREATURE):
            p = _num(getattr(c, 'power', 0))
            t = _num(getattr(c, 'toughness', 0))
            kws = len(getattr(c, 'keywords', []) or [])
            tot += p + 0.5 * t + _KW_BONUS * min(kws, 3)
    return tot


def _state_value(gs, opp) -> float:
    """Terminal evaluation of a completed main phase (my seat's view only)."""
    v = 0.0
    if opp is None:
        class _Empty:
            class zones: battlefield = []
        opp = _Empty

    v += 2.0 * _board_power(gs)                              # board presence
    v += 1.0 * float(getattr(gs, 'damage_dealt', 0) or 0)    # face damage banked
    v -= 2.0 * _board_power(opp)                             # their board
    v += 0.25 * len(getattr(gs.zones, 'hand', []) or [])     # cards in hand
    v += 0.5 * sum(1 for c in (getattr(gs.zones, 'battlefield', []) or [])
                   if c.is_land())                           # development
    v += 0.1 * _num(getattr(gs, 'life', 20), 20)
    return v


def _greedy_complete(gs, opp) -> None:
    """Finish the (forked) main phase greedily: cast cheapest-first until stuck."""
    for _ in range(_MAX_DECISIONS_PER_TURN):
        acts = [a for a in legal_main_actions(gs) if a.kind != 'PASS']
        if not acts:
            return
        lands = [a for a in acts if a.kind == 'PLAY_LAND']
        casts = sorted((a for a in acts if a.kind == 'CAST'),
                       key=lambda a: getattr(a.card_ref, 'cmc', 99))
        nxt = lands[0] if lands else (casts[0] if casts else None)
        if nxt is None or not apply_action(gs, nxt):
            return


class SearchAPL(MatchAPL):
    """Deck-agnostic search pilot. Give it ANY deck; it derives its own turns."""
    name = "Search Prototype"

    def __init__(self):
        # BaseAPL may or may not define __init__ state we need; stay minimal.
        try:
            super().__init__()
        except TypeError:
            pass
        self.decisions = 0
        self.forks = 0

    # ---- mulligan: simple, deck-agnostic, deterministic ----
    def keep(self, hand, mulligans, on_play) -> bool:
        lands = sum(1 for c in hand if c.is_land())
        if mulligans >= 3:
            return True
        lo, hi = (2, 5) if mulligans == 0 else (1, 6)
        return lo <= lands <= hi

    def bottom(self, hand, n) -> list:
        ranked = sorted(hand, key=lambda c: (not c.is_land(),
                                             getattr(c, 'cmc', 0)), reverse=True)
        return ranked[:n]

    def main_phase(self, gs):
        # goldfish-mode entry point (abstract in BaseAPL): search vs empty seat
        self.main_phase_match(gs, None)

    # ---- the searched decision loop ----
    def main_phase_match(self, gs, opponent):
        if not getattr(gs, 'land_played', True):
            pass  # land choice participates in the search below
        gs.tap_lands()

        for _ in range(_MAX_DECISIONS_PER_TURN):
            candidates = legal_main_actions(gs)
            real = [a for a in candidates if a.kind != 'PASS']
            if not real:
                break
            # rank candidates cheaply, fork-evaluate the top _BEAM
            def _prior(a: Action) -> float:
                if a.kind == 'PLAY_LAND':
                    return 100.0
                c = a.card_ref
                p = _num(getattr(c, 'power', 0)) + _num(getattr(c, 'toughness', 0))
                cmc = max(1.0, _num(getattr(c, 'cmc', 1), 1))
                return p / cmc + 0.01 * (10 - cmc)
            ranked = sorted(real, key=_prior, reverse=True)[:_BEAM]

            best, best_v = None, float('-inf')
            for a in ranked:
                g2, o2 = fork(gs, opponent)
                self.forks += 1
                if not apply_action(g2, a):
                    continue
                _greedy_complete(g2, o2)
                v = _state_value(g2, o2)
                if v > best_v:
                    best, best_v = a, v
            # is doing NOTHING better? (hold cards)
            g2, o2 = fork(gs, opponent)
            self.forks += 1
            if _state_value(g2, o2) >= best_v or best is None:
                break
            if not apply_action(gs, best):
                break
            self.decisions += 1

    def main_phase2_match(self, gs, opponent):
        # post-combat: dump remaining playables greedily (no fork needed --
        # nothing left this turn to sequence around)
        gs.tap_lands()
        _greedy_complete(gs, opponent)

    # combat + priority + end-step: MatchAPL's real-Magic defaults (see
    # match_apl.py:366/467/55/518). Deliberately un-searched in v0.
