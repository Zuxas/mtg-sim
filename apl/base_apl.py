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
    ) -> GameResult:
        """
        Run one complete goldfish game.
        Returns a GameResult with kill turn and stats.
        """
        import copy
        result = GameResult()

        # Fresh Card objects each game so counters don't bleed between games
        fresh_deck = copy.deepcopy(mainboard)

        # --- Opening hand ---
        hand, library, mulligans = take_opening_hand(
            deck=fresh_deck,
            keep_fn=self.keep,
            bottom_fn=self.bottom,
            on_play=on_play,
            verbose=verbose,
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
            gs.run_turn()
            gs.tap_lands()

            self.main_phase(gs)

            # Combat is handled by run_turn() internally.
            # main_phase2 handles post-combat plays (haste creatures held back,
            # remaining mana after combat, instants at end of turn).
            gs.phase = "main2"
            gs.mana_pool.empty()
            gs.tap_lands()
            self.main_phase2(gs)
            gs._end()  # EOT cleanup: sacrifice Mobilize tokens, revert Mutavault

            lands_this_turn  = gs.zones.count_lands_in_play()
            spells_this_turn = len(gs.zones.battlefield) - lands_this_turn

            result.lands_played.append(lands_this_turn)
            result.spells_cast.append(spells_this_turn)

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
