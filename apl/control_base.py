"""apl/control_base.py -- Shared control / midrange APL patterns.

Covers decks whose plan is 'answer threats, stick a threat, grind
to victory through card advantage'. Think Esper Raffine, UW Control,
Dimir Midrange.

Real-control decisions the base models:

  1. Proactive vs reactive disruption split. HAND_ATTACK (Thoughtseize,
     Duress) fires on curve regardless of what's in hand — you don't
     hold those for opp's turn. REMOVAL and COUNTERS are reactive —
     you hold them up, only tapping them when they're needed.

  2. Mana reservation. When we have reactive spells in hand, main
     phase 1 leaves their cost up instead of tapping out for threats.
     A T4 with Raffine + Cut Down + Liliana passes with 1 open
     (Cut Down cost) rather than jamming Liliana and leaving nothing.

  3. Threat cadence. Don't deploy threats pre-combat if dropping the
     threat would leave us unable to cast our reactive spells. Either
     sequence the threat post-combat (if we haven't cast a reactive
     yet) or hold it for next turn.

  4. Wipes conditional. _should_wipe(gs) defaults to False (goldfish
     has no opp board); subclasses override for match play.

Subclass declares HAND_ATTACK / REMOVAL / COUNTERS / WIPES / THREATS /
VALUE_SPELLS. The base handles sequencing.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState


class ControlAPL(SBPlanMixin, BaseAPL):
    name = "Generic Control"
    win_condition_damage = 20
    max_turns = 16

    # ── Disruption categories (subclass overrides) ────────────────
    # Proactive hand attack — cast on curve (T1-T2 ideally).
    HAND_ATTACK: tuple = ()

    # Reactive removal — held up through main 1, cast post-combat if
    # not needed (engine doesn't give us an 'opp turn' to hold through).
    REMOVAL: tuple = ()

    # Counterspells — never cast on our own turn; held as mana
    # reservation only. In goldfish these sit in hand all game.
    COUNTERS: tuple = ()

    # Board wipes — cast only when _should_wipe(gs) is True.
    WIPES: tuple = ()

    # ── Threats (cheapest first; biggest-castable chosen per turn) ─
    THREATS: tuple = ()

    # Value spells — card draw, planeswalkers, non-reactive enchantments.
    VALUE_SPELLS: tuple = ()

    # Back-compat: old APIs passed everything in DISRUPTION. If a
    # subclass sets DISRUPTION but not the categorized fields, fall
    # back to REMOVAL semantics.
    DISRUPTION: tuple = ()

    # ── Mulligan thresholds ─────────────────────────────────────────
    MULL_MIN_LANDS = 2
    MULL_MAX_LANDS = 5
    MULL_MIN_DISRUPT_OR_THREAT = 2

    # ------------------------------------------------------------------
    # Public API: normalized disruption list (back-compat + new)
    # ------------------------------------------------------------------

    @property
    def _all_disruption(self) -> tuple:
        """Every disruption name across the four categories.
        Used by the mulligan heuristic."""
        if self.DISRUPTION and not any((self.HAND_ATTACK, self.REMOVAL,
                                        self.COUNTERS, self.WIPES)):
            return self.DISRUPTION
        return self.HAND_ATTACK + self.REMOVAL + self.COUNTERS + self.WIPES

    @property
    def _reactive_spells(self) -> tuple:
        """Disruption we want to keep mana open for. Hand attack and
        wipes fire on-schedule; counters and removal are reactive."""
        return self.REMOVAL + self.COUNTERS

    # ------------------------------------------------------------------
    # Mulligan
    # ------------------------------------------------------------------

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        disrupt = sum(1 for c in hand if c.name in self._all_disruption)
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
    # Mana reservation
    # ------------------------------------------------------------------

    def _reactive_mana_needed(self, gs: GameState) -> int:
        """Return the mana we want to keep open for reactive spells.
        Heuristic: the mana cost of the cheapest reactive card in hand
        — because we only need enough to cast one reactive on opp's
        turn. 0 if no reactive cards are in hand."""
        cheapest = None
        for card in gs.hand():
            if card.name not in self._reactive_spells:
                continue
            cmc = getattr(card, "cmc", 0) or 0
            if cheapest is None or cmc < cheapest:
                cheapest = cmc
        return cheapest or 0

    def _mana_available_for_threat(self, gs: GameState) -> int:
        """Mana we can tap on a threat without losing our reactive
        backup. total_mana - reactive_reserve."""
        return max(0, gs.mana_pool.total() - self._reactive_mana_needed(gs))

    # ------------------------------------------------------------------
    # Main phase 1 (pre-combat)
    # ------------------------------------------------------------------

    def main_phase(self, gs: GameState):
        # 1. Land drop
        self._play_land_if_able(gs)

        # 2. Hand attack — proactive, cast on curve
        self._cast_in_priority(gs, self.HAND_ATTACK, limit=1)

        # 3. Wipe if board state requires it (goldfish default: never)
        if self._should_wipe(gs):
            self._cast_in_priority(gs, self.WIPES, limit=1)

        # 4. Biggest threat that fits within mana_available_for_threat
        # (leaves reactive mana on the table).
        self._cast_biggest_threat_reserved(gs)

        # 5. Value / setup spells — low priority since they compete
        # with reactive mana; fire one at most.
        self._cast_in_priority(gs, self.VALUE_SPELLS, limit=1)

        # 6. Archetype hook
        self._custom_precombat(gs)

    # ------------------------------------------------------------------
    # Main phase 2 (post-combat)
    # ------------------------------------------------------------------

    def main_phase2(self, gs: GameState):
        # By now opponents have had their chance to act. Release any
        # unused reactive mana into things we didn't get to cast.

        # Reactive spells get to go face now (in goldfish there's no
        # opp target to answer anyway — they'd otherwise rot in hand)
        self._cast_in_priority(gs, self.REMOVAL)

        # Second threat pass — main phase 2 without reactive reserve
        self._cast_biggest_threat(gs)

        # Wipes if they weren't cast pre-combat and the board still warrants
        if self._should_wipe(gs):
            self._cast_in_priority(gs, self.WIPES)

        # Value spells fill any leftover mana
        self._cast_in_priority(gs, self.VALUE_SPELLS)

        # Cheap hand attack dumps on turn 5+ when opp is topdecking
        self._cast_in_priority(gs, self.HAND_ATTACK)

        self._custom_postcombat(gs)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _cast_in_priority(self, gs: GameState, names, limit: int = None):
        """Cast spells from `names` in order. If `limit` is set, stop
        after that many successful casts."""
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
        """Main-phase-2 variant: cast biggest castable threat, no
        reactive reserve (opp already had their chance)."""
        for name in reversed(self.THREATS):
            for card in list(gs.hand()):
                if card.name != name:
                    continue
                if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    continue
                gs.cast_spell(card)
                self._after_threat_cast(gs, name, card)
                return

    def _cast_biggest_threat_reserved(self, gs: GameState):
        """Main-phase-1 variant: cast biggest threat that leaves
        reactive mana on the table. If we only have enough mana to
        cast the threat by tapping out below the reactive reserve,
        skip it and wait for main phase 2."""
        reserve = self._reactive_mana_needed(gs)
        for name in reversed(self.THREATS):
            for card in list(gs.hand()):
                if card.name != name:
                    continue
                # Use effective cmc so cost-reductions (GY-scaling
                # Elementals etc.) are visible to the reserve check.
                from engine.game_state import _effective_cmc
                threat_cmc = _effective_cmc(card, gs)
                if not gs.mana_pool.can_cast(card.mana_cost, threat_cmc):
                    continue
                # Would this tap us below the reactive reserve?
                if (gs.mana_pool.total() - threat_cmc) < reserve:
                    continue
                gs.cast_spell(card)
                self._after_threat_cast(gs, name, card)
                return

    # ------------------------------------------------------------------
    # Hooks — override in subclass
    # ------------------------------------------------------------------

    def _should_wipe(self, gs: GameState) -> bool:
        """Return True if we should cast a boardwipe this turn.

        Real-Magic logic: wipe when the board asymmetry favors opp
        (they have more creatures than we do, especially when we're
        behind on life / damage race). Refuses to wipe when our own
        threats are on the board and doing work.

        Goldfish (no opp_gs): never wipe.
        """
        opp = getattr(self, "_opp_gs", None)
        if opp is None:
            return False
        my_creatures = self._my_creature_count(gs)
        opp_creatures = self._opp_creature_count()
        # Core heuristic: opp_creatures exceeds mine by at least 2,
        # OR opp has 4+ and we have 1 or 0.
        if opp_creatures - my_creatures >= 2:
            return True
        if opp_creatures >= 4 and my_creatures <= 1:
            return True
        return False

    # ------------------------------------------------------------------
    # Own-side helpers — stay here since they read gs (our own state).
    # Opp-side helpers now live on MatchAPL so every base class sees
    # them (_opp_creature_count, _opp_hand_size, _opp_untapped_lands,
    # _opp_likely_has_counter, _opp_damage_dealt).
    # ------------------------------------------------------------------

    def _my_creature_count(self, gs: GameState) -> int:
        from data.card import Tag
        return sum(1 for c in gs.zones.battlefield if c.has(Tag.CREATURE))

    def _after_threat_cast(self, gs: GameState, name: str, card):
        """Called after a threat resolves — override for ward mana
        reservation, connive triggers, etc."""
        pass

    def _custom_precombat(self, gs: GameState):
        pass

    def _custom_postcombat(self, gs: GameState):
        pass
