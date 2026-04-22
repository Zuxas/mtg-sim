"""apl/combo_base.py -- Shared combo APL patterns.

Covers decks whose plan is 'assemble pieces → execute a deterministic
kill'. Storm, Amulet Titan, Scapeshift, Grinding Breach all fit.

Unlike Aggro/Ramp/Control, combo decks vary wildly in how they kill
and what their setup looks like, so this base is thin. It provides:

  1. Turn skeleton: land → setup → enablers → try-to-win → cantrips
  2. Mulligan heuristic parameterised on 'need N pieces + some lands'
  3. Hooks for the two hard parts — _can_combo_this_turn() and
     _execute_combo() — which each subclass implements fully.

Subclasses override:
  SETUP_PIECES  (cost reducers, tutors) — cast every turn we can
  ENABLERS      (combo core, e.g. Ral) — cast once, then guard
  CANTRIPS      (draw / filter) — fill the hand between combo turns
  _can_combo_this_turn(gs) -> bool   — 'am I close enough to go?'
  _execute_combo(gs) -> bool         — 'go, return True on kill'

The default main_phase wires them together; subclasses rarely need
to override it.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState


class ComboAPL(SBPlanMixin, BaseAPL):
    name = "Generic Combo"
    win_condition_damage = 20
    max_turns = 12

    # ── Card declarations ───────────────────────────────────────────
    # Setup pieces: cost reducers, tutors, card-draw engines. Cast on
    # their curve turn regardless of combo threshold — they advance
    # every future go-off attempt.
    SETUP_PIECES: tuple = ()

    # Enablers: the must-have combo pieces (e.g. Ral for Storm, Amulet
    # for Amulet Titan). Once one resolves, _ enabler_out flag flips and
    # _can_combo_this_turn can start returning True.
    ENABLERS: tuple = ()

    # Cantrips: cheap draw/filter. Used both to cycle toward combo and
    # to fill a turn where we can't go off yet.
    CANTRIPS: tuple = ()

    # ── Mulligan thresholds ─────────────────────────────────────────
    MULL_MIN_LANDS = 1
    MULL_MAX_LANDS = 3
    MULL_MIN_PIECES = 2        # combo pieces (setup + enabler + cantrip)

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    def __init__(self):
        self._reset_game_state()

    def _reset_game_state(self):
        """Reset per-game combo state. Subclasses can override to
        reset archetype-specific counters (storm count, amulet copies,
        etc.)."""
        self._enabler_on_battlefield = False
        self._spells_cast_this_turn = 0

    def _reset_turn_state(self):
        """Reset per-turn counters. Goldfish game-state also resets
        noncreature_spells_this_turn, but combo decks usually track
        their own storm count separately."""
        self._spells_cast_this_turn = 0

    # ------------------------------------------------------------------
    # Mulligan
    # ------------------------------------------------------------------

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        pieces = sum(
            1 for c in hand
            if c.name in self.SETUP_PIECES
            or c.name in self.ENABLERS
            or c.name in self.CANTRIPS
        )
        if lands < self.MULL_MIN_LANDS or lands > self.MULL_MAX_LANDS:
            return False
        if pieces >= self.MULL_MIN_PIECES:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        if len(lands) > 2:
            return lands[2:][:n]
        # Otherwise ship duplicate enablers (usually legendary or only
        # need one on board)
        if self.ENABLERS:
            heaviest = self.ENABLERS[0]
            dupes = [c for c in hand if c.name == heaviest]
            if len(dupes) >= 2:
                return dupes[1:][:n]
        return lands[2:][:n]

    # ------------------------------------------------------------------
    # Main phase 1
    # ------------------------------------------------------------------

    def main_phase(self, gs: GameState):
        if gs.turn == 1:
            self._reset_game_state()
        self._reset_turn_state()

        # 1. Land
        self._play_land_if_able(gs)

        # 2. Setup pieces first — these make combo cheaper
        self._cast_in_priority(gs, self.SETUP_PIECES)

        # 3. Enablers — the combo core
        self._cast_enablers(gs)

        # 4. Try to win this turn
        if self._can_combo_this_turn(gs):
            if self._execute_combo(gs):
                return

        # 5. Fill the turn with cantrips / setup for next try
        self._cast_in_priority(gs, self.CANTRIPS)

    def main_phase2(self, gs: GameState):
        # One more try after combat (some decks draw during combat /
        # trigger-dependent pieces only come online after attack step)
        if self._can_combo_this_turn(gs):
            self._execute_combo(gs)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _cast_enablers(self, gs: GameState):
        """Deploy any enablers we haven't stuck yet. One per turn, then
        flip the _enabler_on_battlefield flag."""
        if self._enabler_on_battlefield:
            return
        for name in self.ENABLERS:
            # Skip if already on board (legendary rule + didn't recast)
            if any(c.name == name for c in gs.zones.battlefield):
                self._enabler_on_battlefield = True
                return
            for card in list(gs.hand()):
                if card.name != name:
                    continue
                if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    continue
                gs.cast_spell(card)
                self._enabler_on_battlefield = True
                gs._log(f"  Enabler deployed: {name}")
                return

    def _cast_in_priority(self, gs: GameState, names):
        """Cast spells in `names` until no more are castable.
        Calls _after_cantrip_cast hook per successful cast so subclasses
        can handle draw effects, mana refunds, storm counting, etc."""
        changed = True
        while changed:
            changed = False
            for name in names:
                for card in list(gs.hand()):
                    if card.name != name:
                        continue
                    if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        continue
                    gs.cast_spell(card)
                    self._after_cantrip_cast(gs, name, card)
                    changed = True
                    break
                if changed:
                    break

    def _after_cantrip_cast(self, gs: GameState, name: str, card):
        """Hook: called after a cantrip/setup spell resolves. Override
        to draw cards, refund mana, count storm, etc."""
        pass

    # ------------------------------------------------------------------
    # Hooks — subclass must implement the archetype's combo math
    # ------------------------------------------------------------------

    def _can_combo_this_turn(self, gs: GameState) -> bool:
        """Return True if we should try to go off this turn. Default:
        never (subclass must override)."""
        return False

    def _execute_combo(self, gs: GameState) -> bool:
        """Execute the kill sequence. Return True on win (damage >= 20
        or equivalent), False otherwise. Default: no-op."""
        return False
