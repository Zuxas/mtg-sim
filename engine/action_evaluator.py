"""
engine/action_evaluator.py — Model-driven action selection

Replaces the static APL priority list with a learned value function.

At each decision point:
  1. Generate candidate actions (which card to play next)
  2. Simulate the board state AFTER each action (lightweight copy)
  3. Query ML model for P(win | board_state)
  4. Pick highest P(win) action

This is the bridge between rule-based and RL:
  Rule-based:   static priority (Champion > Thalia > ...)
  This module:  evaluate P(win) for each candidate, pick best
  Full RL:      learn the value function from self-play instead of sim data

The model is queried ~3-5 times per turn (for each candidate card).
At T4.35 avg kill with 5 candidates = ~22 model queries per game.
GBM inference is microseconds, so this adds <1ms per game.
"""

from __future__ import annotations
from copy import deepcopy
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from engine.game_state import GameState
    from data.card import Card


def _quick_snap(gs) -> dict:
    """Fast board snapshot without calling gs.snapshot() (avoids overhead)."""
    try:
        bf   = gs.zones.battlefield
        hand = gs.zones.hand

        def is_land(c):
            return hasattr(c, 'is_land') and callable(c.is_land) and c.is_land()

        def pwr(c):
            try:
                ep = getattr(c, 'effective_power', None)
                return ep() if callable(ep) else int(getattr(c, 'power', 0) or 0)
            except Exception:
                return 0

        KEY = {
            "Thalia, Guardian of Thraben":  "has_thalia,_guardian_of_thraben",
            "Champion of the Parish":        "has_champion_of_the_parish",
            "Thalia's Lieutenant":           "has_thalia's_lieutenant",
            "Adeline, Resplendent Cathar":   "has_adeline,_resplendent_cathar",
            "Guide of Souls":                "has_guide_of_souls",
            "Cavern of Souls":               "has_cavern_of_souls",
            "Esper Sentinel":                "has_esper_sentinel",
            "Kytheon, Hero of Akros":        "has_kytheon,_hero_of_akros",
        }
        lands_bf = [c for c in bf if is_land(c)]
        snap = {
            "turn":              gs.turn,
            "damage_dealt":      gs.damage_dealt,
            "creatures_in_play": len(bf),
            "total_power":       min(sum(pwr(c) for c in bf), 40),
            "lands_in_play":     len(lands_bf),
            "hand_size":         len(hand),
            "life":              gs.life,
            "energy":            getattr(gs, 'energy', 0),
            "mulligans":         0,
            "hand_creatures":    sum(1 for c in hand if not is_land(c)),
            "hand_lands":        sum(1 for c in hand if is_land(c)),
        }
        for name, key in KEY.items():
            snap[key] = int(any(c.name == name for c in bf))
        return snap
    except Exception:
        return {"turn": gs.turn, "damage_dealt": gs.damage_dealt,
                "creatures_in_play": 0, "total_power": 0,
                "lands_in_play": 0, "hand_size": 0, "life": 20,
                "energy": 0, "mulligans": 0, "hand_creatures": 0, "hand_lands": 0}


class ActionEvaluator:
    """
    Evaluates candidate actions using the ML win probability model.

    Usage:
        evaluator = ActionEvaluator(model, opp_archetype)
        best_card = evaluator.pick_best(gs, candidates)
    """

    def __init__(self, model, opp_archetype: str):
        self.model        = model
        self.opp_archetype = opp_archetype
        self._cache: dict = {}   # snap hash → P(win)

    def _predict(self, snap: dict) -> float:
        """Query model for P(win). Cached by board state hash."""
        key = (snap["turn"], snap["damage_dealt"], snap["creatures_in_play"],
               snap["total_power"], snap["hand_size"])
        if key in self._cache:
            return self._cache[key]
        try:
            from ml.win_prob_model import predict_win_prob
            p = predict_win_prob(snap, self.opp_archetype, model=self.model)
        except Exception:
            p = 50.0
        self._cache[key] = p
        return p

    def pick_best(self, gs, candidates: list) -> Optional[object]:
        """
        Given a list of candidate Card objects, pick the one that
        maximizes P(win) after being played.

        For each candidate, we simulate playing it (update the board state
        snapshot) and query the model. Returns the card with highest P(win).
        """
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        base_snap = _quick_snap(gs)
        best_card = candidates[0]
        best_p    = -1.0

        for card in candidates:
            # Simulate playing this card: adjust snapshot features
            snap = dict(base_snap)
            snap["hand_size"]         = max(0, snap["hand_size"] - 1)
            snap["hand_creatures"]    = max(0, snap["hand_creatures"] - 1)
            snap["creatures_in_play"] = snap["creatures_in_play"] + 1

            # Estimate power contribution
            try:
                ep = getattr(card, 'effective_power', None)
                card_power = ep() if callable(ep) else int(getattr(card, 'power', 0) or 0)
            except Exception:
                card_power = 2

            snap["total_power"] = min(snap["total_power"] + card_power, 40)

            # Mark key card presence
            key_map = {
                "Thalia, Guardian of Thraben":  "has_thalia,_guardian_of_thraben",
                "Champion of the Parish":        "has_champion_of_the_parish",
                "Thalia's Lieutenant":           "has_thalia's_lieutenant",
                "Adeline, Resplendent Cathar":   "has_adeline,_resplendent_cathar",
                "Guide of Souls":                "has_guide_of_souls",
                "Cavern of Souls":               "has_cavern_of_souls",
                "Esper Sentinel":                "has_esper_sentinel",
                "Kytheon, Hero of Akros":        "has_kytheon,_hero_of_akros",
            }
            if card.name in key_map:
                snap[key_map[card.name]] = 1

            p = self._predict(snap)
            if p > best_p:
                best_p    = p
                best_card = card

        return best_card

    def rank_candidates(self, gs, candidates: list) -> list[tuple]:
        """Return all candidates ranked by P(win), as (card, p) pairs."""
        if not candidates:
            return []
        base_snap = _quick_snap(gs)
        results = []
        for card in candidates:
            snap = dict(base_snap)
            snap["hand_size"]         = max(0, snap["hand_size"] - 1)
            snap["creatures_in_play"] = snap["creatures_in_play"] + 1
            try:
                ep = getattr(card, 'effective_power', None)
                snap["total_power"] = min(snap["total_power"] +
                                          (ep() if callable(ep) else int(getattr(card,'power',0) or 0)), 40)
            except Exception:
                pass
            key_map = {
                "Thalia, Guardian of Thraben":  "has_thalia,_guardian_of_thraben",
                "Champion of the Parish":        "has_champion_of_the_parish",
                "Thalia's Lieutenant":           "has_thalia's_lieutenant",
                "Adeline, Resplendent Cathar":   "has_adeline,_resplendent_cathar",
                "Guide of Souls":                "has_guide_of_souls",
            }
            if card.name in key_map:
                snap[key_map[card.name]] = 1
            p = self._predict(snap)
            results.append((card, round(p, 1)))
        return sorted(results, key=lambda x: -x[1])
