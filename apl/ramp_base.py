"""apl/ramp_base.py -- Shared ramp / big-mana APL patterns.

Covers any deck whose play pattern is 'ramp into big things':

  1. Keep on 3+ lands + at least one ramp/payoff threat
  2. Land drop, prefer fixing lands (triomes) when domain matters
  3. Cast ramp spells (mana dorks, tapped lands, treasure-makers)
  4. Cast removal to survive while ramping
  5. Cast the biggest payoff we can afford (curve planner picks
     most-expensive-castable to maximize mana used)
  6. Post-combat: any leftover mana → cheap removal or extra ramp

Subclass declares RAMP_SPELLS, PAYOFFS, REMOVAL; the base handles
the turn loop and the "spend max mana" curve heuristic.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState


class RampAPL(SBPlanMixin, BaseAPL):
    name = "Generic Ramp"
    win_condition_damage = 20
    max_turns = 15

    # ── Card declarations (subclass overrides) ─────────────────────
    # Name -> (mana_cost, mana_added_or_lands_into_play).
    # mana_added is the +mana effect for this turn; 0 means the
    # ramp is a land-drop advance (Topiary Stomper, Cultivate, etc.)
    # that doesn't add mana this turn but helps future turns.
    RAMP_SPELLS: dict = {}

    # Top-end threats, cheapest-first. Cast biggest affordable each turn.
    PAYOFFS: tuple = ()

    # Removal spells the deck runs. Cheapest-first preferred for
    # tempo-trading; subclasses can reorder.
    REMOVAL: tuple = ()

    # Board wipes — cast when we're behind (but goldfish never is, so
    # these only fire if their mana cost is paid with nothing better
    # to do).
    BOARDWIPES: tuple = ()

    # ── Mulligan thresholds ─────────────────────────────────────────
    MULL_MIN_LANDS = 3          # ramp needs lots of lands
    MULL_MAX_LANDS = 6
    MULL_MIN_RAMP_OR_PAYOFF = 1

    # ------------------------------------------------------------------
    # Mulligan
    # ------------------------------------------------------------------

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        ramp = sum(1 for c in hand if c.name in self.RAMP_SPELLS)
        payoff = sum(1 for c in hand if c.name in self.PAYOFFS)
        if lands < 2 or lands > self.MULL_MAX_LANDS:
            return False
        if (self.MULL_MIN_LANDS <= lands <= self.MULL_MAX_LANDS
                and (ramp + payoff) >= self.MULL_MIN_RAMP_OR_PAYOFF):
            return True
        # Softer keep when we already have 2 lands + both a ramp and a payoff
        if lands == 2 and ramp >= 1 and payoff >= 1:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        if len(lands) > 5:
            return lands[5:][:n]
        # Ship extra copies of the biggest payoff (we only need one)
        if self.PAYOFFS:
            heaviest = self.PAYOFFS[-1]
            extras = [c for c in hand if c.name == heaviest]
            if len(extras) >= 2:
                return extras[1:][:n]
        # Last resort: ship removal (can't target in goldfish)
        removal = [c for c in hand if c.name in self.REMOVAL]
        return removal[:n] + lands[5:][:max(0, n - len(removal))]

    # ------------------------------------------------------------------
    # Main phase 1
    # ------------------------------------------------------------------

    def main_phase(self, gs: GameState):
        # 1. Land — prefer fixing lands for domain decks
        self._play_best_land(gs)

        # 2. Ramp spells first — curves out future turns
        for name in self.RAMP_SPELLS:
            for card in list(gs.hand()):
                if card.name != name:
                    continue
                if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    continue
                gs.cast_spell(card)
                mana_added = self.RAMP_SPELLS[name][1]
                if mana_added > 0:
                    gs.mana_pool.flex += mana_added
                    gs._log(f"  {name}: +{mana_added} mana this turn "
                            f"({gs.mana_pool.total()} total)")
                self._after_ramp_cast(gs, name, card)
                break

        # 3. Cast the biggest payoff we can afford (maximize mana used
        # per turn — that's the entire point of ramp)
        self._cast_biggest_payoff(gs)

        # 4. Removal / wipes with any leftover mana
        self._cast_removal(gs)

        # Archetype-specific hook
        self._custom_precombat(gs)

    def main_phase2(self, gs: GameState):
        # Cast more payoffs if the combat step left mana (Atraxa-draw
        # scenarios, Archangel kicker, etc.)
        self._cast_biggest_payoff(gs)
        self._cast_removal(gs)
        self._custom_postcombat(gs)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _play_best_land(self, gs: GameState):
        """Land-drop priority: fixing lands (triomes / verges) first
        so domain / multi-color becomes castable sooner. Falls back to
        BaseAPL._play_land_if_able for singles."""
        if gs.land_played:
            return
        # Prefer non-basic, non-enters-tapped-painful lands
        hand_lands = [c for c in gs.hand() if c.is_land()]
        if not hand_lands:
            return
        # Sort: type_line containing multiple basic land types wins (triomes)
        def _land_score(card):
            tl = (getattr(card, "type_line", "") or "").lower()
            score = 0
            for t in ("plains", "island", "swamp", "mountain", "forest"):
                if t in tl:
                    score += 1
            return score
        hand_lands.sort(key=_land_score, reverse=True)
        best = hand_lands[0]
        gs.zones.play_from_hand(best)
        gs.mana_pool.flex += 1
        gs._log(f"  Land: {best.name}")

    def _cast_biggest_payoff(self, gs: GameState):
        """Cast the most-expensive payoff we can afford. Ramp decks
        want to maximize mana-used-per-turn, not curve out cheapest."""
        # Iterate payoffs in reverse priority (biggest first)
        for name in reversed(self.PAYOFFS):
            for card in list(gs.hand()):
                if card.name != name:
                    continue
                if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    continue
                gs.cast_spell(card)
                self._after_payoff_cast(gs, name, card)
                return   # one payoff per phase — don't double-spend

    def _cast_removal(self, gs: GameState):
        """Cast removal with leftover mana. In goldfish there's
        nothing to target, but spells still resolve and are burnt."""
        for name in self.REMOVAL:
            for card in list(gs.hand()):
                if card.name != name:
                    continue
                if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    continue
                gs.cast_spell(card)
                break

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def _after_ramp_cast(self, gs: GameState, name: str, card):
        pass

    def _after_payoff_cast(self, gs: GameState, name: str, card):
        pass

    def _custom_precombat(self, gs: GameState):
        pass

    def _custom_postcombat(self, gs: GameState):
        pass
