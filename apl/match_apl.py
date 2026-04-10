"""
apl/match_apl.py — Extended APL interface for two-player matchup simulation

MatchAPL extends BaseAPL with opponent-aware methods:
- declare_attackers: choose which creatures attack (seeing opponent board)
- declare_blockers: assign blockers to opponent's attackers
- respond_to_spell: counter/kill in response to opponent casting
- end_step_actions: flash creatures, instants at end of opponent's turn

GoldfishAdapter wraps existing goldfish APLs to work in match mode.
This means ALL 15+ existing APLs work immediately in Phase 3.
"""

from __future__ import annotations
from abc import abstractmethod
from typing import Optional

from apl.base_apl import BaseAPL
from engine.game_state import GameState
from engine.match_state import (
    MatchGameState, optimal_blocking, safe_power, has_keyword
)
from data.card import Card, Tag


class MatchAPL(BaseAPL):
    """
    Extended APL interface for two-player games.
    Inherits keep/bottom from BaseAPL, adds opponent-aware methods.
    """

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """
        Main phase with opponent awareness.
        Default: falls back to goldfish main_phase.
        Override in hand-tuned match APLs for opponent-aware play.
        """
        self.main_phase(gs)

    def declare_attackers(self, gs: GameState, opponent: GameState) -> list[Card]:
        """
        Choose which creatures attack.
        Default: attack with everything that can (aggressive).
        Override for decks that want to hold back blockers.
        """
        return [c for c in gs.zones.battlefield
                if not c.is_land()
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs: GameState, opponent: GameState,
                          attackers: list[Card]) -> dict:
        """
        Assign blockers to opponent's attackers.
        Default: use optimal blocking algorithm.
        Returns {attacker_card: [blocker_cards]}.
        """
        my_creatures = [c for c in gs.zones.battlefield
                        if not c.is_land()
                        and not getattr(c, 'tapped', False)]
        attacker_clock = 99
        opp_creatures = [c for c in opponent.zones.battlefield if not c.is_land()]
        opp_power = sum(safe_power(c) for c in opp_creatures
                        if not getattr(c, 'summoning_sickness', False))
        if opp_power > 0:
            attacker_clock = max(1, -(-gs.life // opp_power))
        return optimal_blocking(my_creatures, attackers, gs.life, attacker_clock)

    def respond_to_spell(self, gs: GameState, opponent: GameState,
                          spell: Card) -> Optional[Card]:
        """
        Respond to opponent casting a spell.
        Return a card from hand to cast in response, or None.
        Default: no response (goldfish behavior).
        """
        return None

    def end_step_actions(self, gs: GameState, opponent: GameState):
        """
        Actions at end of opponent's turn (flash creatures, instants).
        Default: do nothing.
        """
        pass

    def combat_trick(self, gs: GameState, opponent: GameState,
                      attackers: list[Card], blockers: dict) -> Optional[Card]:
        """
        Play an instant during combat (after blockers declared).
        Default: do nothing.
        """
        return None


class GoldfishAdapter(MatchAPL):
    """
    Wraps any existing goldfish APL to work in match mode.
    
    This is the bridge that makes ALL 15+ existing APLs work in Phase 3
    without any modification. The adapter:
    - Delegates keep/bottom/main_phase to the inner goldfish APL
    - Uses default aggressive attacking (send everything)
    - Uses optimal blocking algorithm for defense
    - Does not respond to spells (goldfish behavior)
    
    Hand-tuned match APLs can subclass MatchAPL directly for
    opponent-aware play (hold removal, counter key spells, etc.).
    """

    def __init__(self, goldfish_apl: BaseAPL):
        self.inner = goldfish_apl
        self.name = goldfish_apl.name

    def keep(self, hand, mulligans, on_play) -> bool:
        return self.inner.keep(hand, mulligans, on_play)

    def bottom(self, hand, n) -> list:
        return self.inner.bottom(hand, n)

    def main_phase(self, gs: GameState):
        """Delegate to inner goldfish APL."""
        self.inner.main_phase(gs)

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """Goldfish APLs ignore the opponent — just play their game."""
        self.inner.main_phase(gs)


class GenericMatchAPL(MatchAPL):
    """
    Generic match APL for decks without a hand-tuned APL.
    Plays creatures by CMC, attacks with everything, blocks optimally.
    """
    name = "Generic"

    def keep(self, hand, mulligans, on_play) -> bool:
        lands = sum(1 for c in hand if c.is_land())
        if mulligans >= 2:
            return lands >= 1
        return 2 <= lands <= 5

    def bottom(self, hand, n) -> list:
        # Bottom excess lands first, then highest CMC
        lands = sorted([c for c in hand if c.is_land()],
                       key=lambda c: 0)
        nonlands = sorted([c for c in hand if not c.is_land()],
                          key=lambda c: -getattr(c, 'cmc', 0))
        pool = lands[3:] + nonlands  # keep up to 3 lands
        return pool[:n]

    def main_phase(self, gs: GameState):
        """Simple: play a land, then curve out creatures by CMC."""
        hand = gs.zones.hand
        bf = gs.zones.battlefield

        # Play a land
        if not gs.land_played:
            lands = [c for c in hand if c.is_land()]
            if lands:
                gs.play_land(lands[0])

        # Tap lands for mana
        gs.tap_lands()

        # Cast creatures by CMC
        changed = True
        while changed:
            changed = False
            castable = [c for c in gs.zones.hand
                        if not c.is_land()
                        and hasattr(c, 'cmc')
                        and c.cmc <= gs.mana_pool.total()
                        and c.cmc > 0]
            if castable:
                spell = min(castable, key=lambda c: c.cmc)
                if gs.cast_spell(spell):
                    changed = True
                else:
                    # Cast failed (wrong colors etc) — skip this spell
                    break
