"""
base_apl.py — Abstract base class for archetype Action Priority Lists

Every archetype APL subclasses BaseAPL and implements:
  - keep(hand, mulligans, on_play)  -> bool
  - bottom(hand, n)                 -> list[Card]
  - main_phase(game_state)          -> None  (make all decisions for the turn)

The runner calls run_game() which handles the full game loop.
"""

from abc import ABC, abstractmethod
from typing import Optional

from data.card import Card, Tag
from engine.game_state import GameState, GameResult, Phase
from engine.zones import Zones
from engine.mana import ManaPool
from apl.mulligan import take_opening_hand


class BaseAPL(ABC):

    # Override in subclass to give the deck a name
    name: str = "Unknown Archetype"

    # Win condition: damage threshold (20 for normal, lower to model racing)
    win_condition_damage: int = 20

    # Max turns before we call the game a loss (prevents infinite loops)
    max_turns: int = 15

    # -----------------------------------------------------------------------
    # Abstract interface — implement these in each archetype
    # -----------------------------------------------------------------------

    @abstractmethod
    def keep(self, hand: list[Card], mulligans: int, on_play: bool) -> bool:
        """Return True to keep this opening hand."""
        ...

    @abstractmethod
    def bottom(self, hand: list[Card], n: int) -> list[Card]:
        """Choose n cards to put on the bottom after a mulligan."""
        ...

    @abstractmethod
    def main_phase(self, gs: GameState):
        """
        Make all decisions for the main phase of the current turn.
        Call gs.play_land(), gs.cast_spell(), etc. here.
        The engine handles untap/draw/combat/end automatically.
        """
        ...

    # -----------------------------------------------------------------------
    # Game loop — called by the Monte Carlo runner
    # -----------------------------------------------------------------------

    def run_game(
        self,
        mainboard: list[Card],
        on_play: bool = True,
        seed: Optional[int] = None,
        verbose: bool = False,
        opp_archetype: str = "",
    ) -> GameResult:
        """
        Run one complete goldfish game.

        opp_archetype: opponent deck name passed to keep_vs() and sideboard logic.
        Returns a GameResult with kill turn and stats.
        """
        import copy
        result = GameResult()

        fresh_deck = copy.deepcopy(mainboard)

        # --- Opening hand with opponent-aware mulligan ---
        keep_fn = self.keep_vs if hasattr(self, 'keep_vs') else self.keep
        hand, library, mulligans = take_opening_hand(
            deck=fresh_deck,
            keep_fn=keep_fn,
            bottom_fn=self.bottom,
            on_play=on_play,
            verbose=verbose,
            opp_archetype=opp_archetype,
        )

        result.mulligans    = mulligans
        result.opening_hand = [c.name for c in hand]

        # --- Initialize game state ---
        gs = GameState(mainboard=mainboard, on_play=on_play)
        gs.new_game()
        gs.zones.hand    = hand
        gs.zones.library = library

        if verbose:
            print(f"\n--- {self.name} | {'Play' if on_play else 'Draw'} "
                  f"| {mulligans} mull ---")
            print(f"  Opening hand: {result.opening_hand}")

        # --- Turn loop ---
        for _ in range(self.max_turns):
            # Untap, upkeep, draw
            gs.run_turn()

            # ── Main Phase 1: play land, cast pre-combat spells ──
            gs.phase = Phase.MAIN1
            gs.tap_lands()
            self.main_phase(gs)

            # ── Combat ──
            gs.run_combat()

            # ── Main Phase 2: cast post-combat spells with leftover mana ──
            gs.phase = Phase.MAIN2
            self.main_phase2(gs)

            # ── End step ──
            gs._end()

            lands_this_turn  = gs.zones.count_lands_in_play()
            spells_this_turn = len(gs.zones.battlefield) - lands_this_turn

            result.lands_played.append(lands_this_turn)
            result.spells_cast.append(spells_this_turn)

            # Capture turn snapshot for ML training
            result.turn_snapshots.append(gs.snapshot())

            if verbose:
                bf = [c.name for c in gs.zones.battlefield
                      if not c.is_land()]
                print(f"  T{gs.turn} end — {gs.damage_dealt} dmg | "
                      f"BF: {bf}")

            if gs.has_won(self.win_condition_damage):
                result.won       = True
                result.kill_turn = gs.turn
                if verbose:
                    print(f"  *** Won on turn {gs.turn} "
                          f"({gs.damage_dealt} damage) ***")
                break

        result.turn_count = gs.turn
        return result

    def main_phase2(self, gs: GameState):
        """
        Main Phase 2 — after combat. Default: cast anything still in hand.
        Override in APLs that need to hold cards for post-combat timing
        (e.g. haste creatures, flash spells, end-of-turn value plays).
        """
        self._cast_all_castable(gs)

    # -----------------------------------------------------------------------
    # Sideboard interface — override per deck with real SB plans
    # -----------------------------------------------------------------------

    def sideboard_premium(self, opp_name: str, format_name: str) -> float:
        """
        Estimated win% improvement from sideboarding against this opponent.
        This is the DELTA added to G1 win rate to get the G2/G3 win rate.

        Override in each deck APL with matchup-specific logic based on:
          - Which SB cards are live (hate pieces, answers, threats)
          - How many SB slots we're dedicating to this matchup
          - Whether the cards fundamentally change the game plan

        Default fallback: generic formula by opponent type.
        Returns a float in percent (e.g. 10.0 = +10%)
        """
        opp = opp_name.lower()
        # Guess from opponent archetype keyword
        if any(k in opp for k in ("reanimator", "breakfast", "combo", "doomsday", "sneak")):
            return 12.0   # dedicated hate pieces
        if any(k in opp for k in ("tron", "titan", "breach", "neoform", "lotus")):
            return 10.0   # hate + disruption
        if any(k in opp for k in ("tempo", "control", "delver", "murktide")):
            return 4.0    # swap interaction, low delta
        if any(k in opp for k in ("aggro", "burn", "mono red", "prowess")):
            return 8.0    # stabilization cards
        return 6.0        # generic

    def keep_vs(self, hand: list, mulligans: int, on_play: bool,
                opp_archetype: str) -> bool:
        """
        Opponent-aware mulligan decision.
        Calls keep() by default. Override for decks where the keep criteria
        change significantly depending on what you're facing.

        Examples:
          - vs combo: keep ANY hand with a clock + 2 lands (speed beats quality)
          - vs Reanimator: keep if you have GY hate OR a T1-T2 kill clock
          - vs Control: keep any fair 2-lander, don't fish for perfect hands
        """
        return self.keep(hand, mulligans, on_play)

    # -----------------------------------------------------------------------
    # Draw spell helpers
    # -----------------------------------------------------------------------

    def _resolve_brainstorm(self, gs: GameState) -> bool:
        """
        Resolve Brainstorm: draw 3, put 2 back on top.
        In goldfish context: draw 3, put back the 2 worst cards.
        Returns True if Brainstorm was found and cast.
        """
        brainstorms = [c for c in gs.hand() if c.name == "Brainstorm"
                       and gs.mana_pool.can_cast(c.mana_cost, c.cmc)]
        if not brainstorms:
            return False
        bs = brainstorms[0]
        gs.cast_spell(bs)
        drawn = gs.zones.draw(3)
        # Put back 2 worst: excess lands first, then highest CMC non-threats
        hand = gs.zones.hand
        def card_value(c):
            if c.is_land() and gs.zones.count_lands_in_play() >= gs.turn:
                return 0  # excess land — put back
            return c.cmc
        to_bottom = sorted(hand, key=card_value)[:2]
        for card in to_bottom:
            gs.zones.hand.remove(card)
            gs.zones.library.insert(0, card)
        return True

    def _resolve_ponder(self, gs: GameState) -> bool:
        """
        Resolve Ponder: look at top 3, arrange or shuffle, draw 1.
        Simplified: draw 1 (net effect of Ponder in a goldfish context).
        """
        ponders = [c for c in gs.hand() if c.name == "Ponder"
                   and gs.mana_pool.can_cast(c.mana_cost, c.cmc)]
        if not ponders:
            return False
        gs.cast_spell(ponders[0])
        gs.zones.draw(1)
        return True

    def _resolve_cantrips(self, gs: GameState):
        """Cast any cantrips in hand (Brainstorm, Ponder, Opt)."""
        self._resolve_brainstorm(gs)
        self._resolve_ponder(gs)
        # Opt, Consider, etc.
        for name in ("Opt", "Consider", "Serum Visions"):
            for c in list(gs.hand()):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    gs.zones.draw(1)
                    break

    def _cheapest_castable(
        self,
        gs: GameState,
        tag_filter: Optional[str] = None,
    ) -> Optional[Card]:
        """
        Return the cheapest castable card in hand.
        Optionally filter by tag (e.g. Tag.CREATURE).
        """
        candidates = [
            c for c in gs.hand()
            if not c.is_land()
            and gs.mana_pool.can_cast(c.mana_cost, c.cmc)
            and (tag_filter is None or c.has(tag_filter))
        ]
        return min(candidates, key=lambda c: c.cmc) if candidates else None

    def _best_land(self, gs: GameState) -> Optional[Card]:
        """Return the best land to play. Default: first land in hand."""
        lands = [c for c in gs.hand() if c.is_land()]
        return lands[0] if lands else None

    def _play_land_if_able(self, gs: GameState) -> bool:
        land = self._best_land(gs)
        if land:
            return gs.play_land(land)
        return False

    def _cast_all_castable(self, gs: GameState, tag_filter: Optional[str] = None):
        """Cast every castable card (lowest CMC first) until out of mana."""
        while True:
            card = self._cheapest_castable(gs, tag_filter)
            if not card:
                break
            if not gs.cast_spell(card):
                break
