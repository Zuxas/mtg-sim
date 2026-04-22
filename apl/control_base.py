"""apl/control_base.py -- Shared control / midrange APL patterns.

Covers decks whose plan is 'answer threats, stick a threat, grind
to victory through card advantage'. Think Esper Raffine, UW Control,
Dimir Midrange.

Pattern:
  1. Mulligan for 2-4 lands + disruption + at least one threat
  2. Land drop
  3. Cast cheap disruption first (hand attack, early removal)
  4. Deploy threats in order of value density (Raffine, Jace,
     Sheoldred) — preferring ward / protected threats
  5. Late-game: draw-go with answers / value engines active
  6. Post-combat: cast cantrips or value spells that don't care
     about combat

Subclass declares DISRUPTION (hand attack + removal), THREATS,
VALUE_SPELLS; the base handles priority + order-of-operations.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState


class ControlAPL(SBPlanMixin, BaseAPL):
    name = "Generic Control"
    win_condition_damage = 20
    max_turns = 16

    # ── Card declarations ───────────────────────────────────────────
    # Disruption cast cheapest-first — hand attack, counters, removal.
    DISRUPTION: tuple = ()

    # Threats in value order (highest density first). Cast one per
    # turn when mana allows.
    THREATS: tuple = ()

    # Value spells: card draw, planeswalkers, enchantments that
    # don't care about combat. Cast post-combat with leftover mana.
    VALUE_SPELLS: tuple = ()

    # ── Mulligan thresholds ─────────────────────────────────────────
    MULL_MIN_LANDS = 2
    MULL_MAX_LANDS = 5
    MULL_MIN_DISRUPT_OR_THREAT = 2

    # ------------------------------------------------------------------
    # Mulligan
    # ------------------------------------------------------------------

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        disrupt = sum(1 for c in hand if c.name in self.DISRUPTION)
        threats = sum(1 for c in hand if c.name in self.THREATS)
        if lands < self.MULL_MIN_LANDS or lands > self.MULL_MAX_LANDS:
            return False
        if (disrupt + threats >= self.MULL_MIN_DISRUPT_OR_THREAT
                and (disrupt >= 1 or threats >= 1)):
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        if len(lands) > 4:
            return lands[4:][:n]
        # Ship the most-expensive threat (we only need one or two hits)
        if self.THREATS:
            heaviest = self.THREATS[-1]
            extras = [c for c in hand if c.name == heaviest]
            if len(extras) >= 2:
                return extras[1:][:n]
        # Otherwise duplicate value spells
        value_dupes: list = []
        for name in self.VALUE_SPELLS:
            dupes = [c for c in hand if c.name == name]
            if len(dupes) >= 2:
                value_dupes.extend(dupes[1:])
        return value_dupes[:n] + lands[4:][:max(0, n - len(value_dupes))]

    # ------------------------------------------------------------------
    # Main phase 1
    # ------------------------------------------------------------------

    def main_phase(self, gs: GameState):
        # 1. Land drop
        self._play_land_if_able(gs)

        # 2. Cheap disruption first — clears path / strips threats
        self._cast_in_priority(gs, self.DISRUPTION, limit=1)

        # 3. One threat per turn (maximize density, not curve-out)
        self._cast_biggest_threat(gs)

        # 4. Value / setup spells
        self._cast_in_priority(gs, self.VALUE_SPELLS, limit=1)

        # 5. Archetype hook
        self._custom_precombat(gs)

    def main_phase2(self, gs: GameState):
        # Post-combat: anything we didn't get to, in value order
        self._cast_in_priority(gs, self.DISRUPTION)
        self._cast_biggest_threat(gs)
        self._cast_in_priority(gs, self.VALUE_SPELLS)
        self._custom_postcombat(gs)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _cast_in_priority(self, gs: GameState, names, limit: int = None):
        """Cast spells from `names` in order, one per matching name.
        If `limit` is set, stop after that many successful casts."""
        cast_count = 0
        for name in names:
            if limit is not None and cast_count >= limit:
                return
            for card in list(gs.hand()):
                if card.name != name:
                    continue
                if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    continue
                gs.cast_spell(card)
                cast_count += 1
                break

    def _cast_biggest_threat(self, gs: GameState):
        """Cast the most-expensive threat we can afford (control decks
        want to lean into their mana — dropping Raffine / Sheoldred over
        a 2-drop when both are castable)."""
        # THREATS is cheapest-first by convention; iterate reversed to
        # prefer biggest when multiple are castable.
        for name in reversed(self.THREATS):
            for card in list(gs.hand()):
                if card.name != name:
                    continue
                if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    continue
                gs.cast_spell(card)
                self._after_threat_cast(gs, name, card)
                return

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def _after_threat_cast(self, gs: GameState, name: str, card):
        """Called after a threat resolves — override for ward mana
        reservation, connive triggers, etc."""
        pass

    def _custom_precombat(self, gs: GameState):
        pass

    def _custom_postcombat(self, gs: GameState):
        pass
