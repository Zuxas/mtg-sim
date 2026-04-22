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
        Default: falls back to goldfish main_phase but stashes the
        opponent GS on self so base-class hooks (ControlAPL's
        _should_wipe, AggroAPL's _should_hold_threat, etc.) can
        consult the opp board when deciding plays.
        """
        self._opp_gs = opponent
        self.main_phase(gs)

    # ------------------------------------------------------------------
    # Opp-state helpers — available to every composed APL in match
    # mode. Goldfish (no _opp_gs) returns 0 / empty from all of these,
    # which reduces to 'play proactively' for every caller.
    # ------------------------------------------------------------------

    def _opp_creature_count(self) -> int:
        opp = getattr(self, "_opp_gs", None)
        if opp is None:
            return 0
        return sum(1 for c in opp.zones.battlefield if c.has(Tag.CREATURE))

    def _opp_hand_size(self) -> int:
        opp = getattr(self, "_opp_gs", None)
        if opp is None:
            return 0
        return len(opp.zones.hand)

    def _opp_untapped_lands(self) -> int:
        opp = getattr(self, "_opp_gs", None)
        if opp is None:
            return 0
        return sum(1 for c in opp.zones.battlefield
                   if c.is_land() and not getattr(c, "tapped", False))

    def _opp_likely_has_counter(self) -> bool:
        """True when opp has cards in hand AND >=2 untapped lands —
        classic counterspell representation."""
        return self._opp_hand_size() >= 1 and self._opp_untapped_lands() >= 2

    def _opp_damage_dealt(self) -> int:
        """How much damage the opp has accrued against us."""
        opp = getattr(self, "_opp_gs", None)
        if opp is None:
            return 0
        return getattr(opp, "damage_dealt", 0)

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
        Respond to opponent's board state with an instant.
        Returns a card from hand to cast, or None.
        Default: use removal on biggest threat if available.
        """
        from engine.stack import classify_card, InteractionType
        
        # Find instants we could cast
        for c in gs.zones.hand:
            if not (c.has(Tag.INSTANT) or c.has(Tag.SORCERY)):
                continue
            if not hasattr(c, 'cmc') or c.cmc > gs.mana_pool.total():
                continue
            itype = classify_card(c)
            
            # Use removal if opponent has a creature worth killing
            if itype in (InteractionType.REMOVAL, InteractionType.BURN):
                opp_creatures = [x for x in opponent.zones.battlefield
                                 if not x.is_land()]
                if opp_creatures:
                    from engine.match_state import safe_power
                    best = max(opp_creatures, key=lambda x: safe_power(x))
                    if safe_power(best) >= 2:  # worth removing
                        return c
            
            # Use discard early game
            if itype == InteractionType.DISCARD and gs.turn <= 2:
                return c
        
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
    Generic match APL — uses removal, burns face, casts all spells.
    Used by decks without a hand-tuned APL (12 of 15 Modern decks).
    """
    name = "Generic"

    def keep(self, hand, mulligans, on_play) -> bool:
        lands = sum(1 for c in hand if c.is_land())
        creatures = sum(1 for c in hand if c.has(Tag.CREATURE))
        if mulligans >= 2: return lands >= 1
        if lands == 0: return False
        if lands > 5: return False
        if creatures == 0 and mulligans < 2: return False
        return 2 <= lands <= 4

    def bottom(self, hand, n) -> list:
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: 0)
        nonlands = sorted([c for c in hand if not c.is_land()],
                          key=lambda c: -getattr(c, 'cmc', 0))
        pool = lands[3:] + nonlands
        return pool[:n]

    def main_phase(self, gs: GameState):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """Opponent-aware: removal on creatures, burn face, cast all spells."""
        hand = gs.zones.hand
        if not gs.land_played:
            lands = [c for c in hand if c.is_land()]
            if lands:
                gs.play_land(lands[0])
        gs.tap_lands()

        # 1. Removal on opponent's best creature
        if opponent:
            self._try_removal(gs, opponent)

        # 2. Cast all spells by CMC (creatures first)
        changed = True
        attempts = 0
        while changed and attempts < 20:
            changed = False
            attempts += 1
            castable = [c for c in gs.zones.hand
                        if not c.is_land()
                        and hasattr(c, 'cmc')
                        and c.cmc <= gs.mana_pool.total()
                        and c.cmc > 0]
            if castable:
                creatures = [c for c in castable if c.has(Tag.CREATURE)]
                spell = min(creatures if creatures else castable, key=lambda c: c.cmc)
                if gs.cast_spell(spell):
                    changed = True
                else:
                    break

        # 3. Burn face
        for c in list(gs.zones.hand):
            oracle = (getattr(c, 'oracle_text', '') or '').lower()
            if c.name.lower() == 'lightning bolt' and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                gs.damage_dealt += 3
                gs.noncreature_spells_this_turn += 1
                break
            elif 'damage' in oracle and 'any target' in oracle and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                from engine.stack import get_burn_damage
                dmg = get_burn_damage(c)
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                gs.damage_dealt += dmg
                gs.noncreature_spells_this_turn += 1
                break

    def _try_removal(self, gs: GameState, opponent: GameState):
        """Use removal on opponent's biggest creature."""
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures: return
        from engine.match_state import safe_power, safe_toughness
        from engine.stack import classify_card, InteractionType, get_burn_damage
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 2: return
        for c in list(gs.zones.hand):
            itype = classify_card(c)
            if itype not in (InteractionType.REMOVAL, InteractionType.BURN): continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc): continue
            if itype == InteractionType.BURN:
                if get_burn_damage(c) < safe_toughness(target): continue
            gs.mana_pool.pay(c.mana_cost, c.cmc)
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            gs.noncreature_spells_this_turn += 1
            if target in opponent.zones.battlefield:
                opponent.zones.battlefield.remove(target)
                opponent.zones.graveyard.append(target)
            return
