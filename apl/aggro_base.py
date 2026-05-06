"""apl/aggro_base.py -- Shared aggro / burn APL patterns.

Extracted from apl/boros_aggro_standard.py. Covers the common shape
of every linear aggro or burn deck:

  1. Keep on 2-4 lands + N threats (creatures + burn)
  2. Land drop, then deploy creatures cheapest-first
  3. Pre-combat burn for prowess pump + face damage
  4. Pump spell on biggest attacker (Monstrous Rage, Embercleave, etc.)
  5. Combat (engine handles prowess/haste)
  6. Post-combat burn straight to face
  7. Late creatures for next turn

Subclasses override class-level declarations to supply their deck's
cards and priorities. Hook methods let them inject archetype-specific
triggers (e.g. Kumano ETB on Boros Aggro) without reimplementing the
full turn loop.

Usage:
    class MonoRedAggroStandardAPL(AggroAPL):
        name = "Mono Red Aggro"
        CREATURES  = (HIRED_CLAW, EMBERHEART, ...)
        BURN_SPELLS = {BURST: (1, 2), LIGHTNING: (2, 3), ...}
        PUMP_SPELLS = {MONSTROUS_RAGE: (1, 2, True)}
        HASTE_CREATURES = {HIRED_CLAW, ...}

Each class attribute is consulted at runtime, so subclasses don't
need to override any methods for the default flow to work.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState
from engine.keywords import KWTag


class AggroAPL(SBPlanMixin, BaseAPL):
    """Base class for linear-aggro / burn decks. Subclass + set the
    class attributes below; you typically don't need to override any
    method for a standard build."""

    # ── Archetype-wide defaults ─────────────────────────────────────
    name = "Generic Aggro"
    win_condition_damage = 20
    max_turns = 12

    # ── Card declarations (subclass overrides) ─────────────────────
    # Cheapest-first list of creature/enchantment names the deck wants
    # to deploy. Threats that enter the battlefield go here.
    CREATURES: tuple = ()

    # Name -> (mana_cost, face_damage). Used both to check castability
    # and to increment gs.damage_dealt when the burn resolves.
    BURN_SPELLS: dict = {}

    # Name -> (mana_cost, +power, grants_trample). Applied to the
    # biggest attacker once per turn via _try_pump().
    PUMP_SPELLS: dict = {}

    # Creature names that enter with haste (get summoning_sickness
    # cleared + KWTag.HASTE applied on cast).
    HASTE_CREATURES: set = frozenset()

    # Cantrips / draw spells cast pre-combat for prowess triggers.
    # Their card-specific draw effect fires via engine/card_effects.py
    # SPELL_EFFECTS registry; this tuple just orders the casts.
    CANTRIP_SPELLS: tuple = ()

    # ── Mulligan thresholds (subclass can tune) ────────────────────
    MULL_MIN_LANDS = 2         # fewer = mulligan
    MULL_MAX_LANDS = 4         # more = mulligan
    MULL_MIN_THREATS = 3       # creatures + burn count
    MULL_ONE_LAND_OK = True    # keep 1-land hands with critical mass

    # ------------------------------------------------------------------
    # Turn bookkeeping
    # ------------------------------------------------------------------

    def reset_game(self):
        self._pump_applied_this_turn = False

    def reset_turn(self):
        self._pump_applied_this_turn = False

    # ------------------------------------------------------------------
    # Mulligan
    # ------------------------------------------------------------------

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        creatures = sum(1 for c in hand
                        if c.name in self.CREATURES and not _is_enchantment(c))
        burn = sum(1 for c in hand if c.name in self.BURN_SPELLS)
        if lands == 0:
            return False
        if lands > self.MULL_MAX_LANDS:
            return False
        if (self.MULL_MIN_LANDS <= lands <= self.MULL_MAX_LANDS
                and creatures + burn >= self.MULL_MIN_THREATS
                and creatures >= 1):
            return True
        if (self.MULL_ONE_LAND_OK and lands == 1
                and creatures >= 2 and burn >= 2):
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        if len(lands) > 3:
            return lands[3:][:n]
        # Otherwise bottom top-end creatures to dig for early drops.
        # Last 25% of the priority list is treated as "top-end".
        top_end_start = max(1, int(len(self.CREATURES) * 0.75))
        top_end_names = set(self.CREATURES[top_end_start:])
        tops = [c for c in hand if c.name in top_end_names]
        return tops[:n] + lands[3:][:max(0, n - len(tops))]

    # ------------------------------------------------------------------
    # Main phase 1 (pre-combat)
    # ------------------------------------------------------------------

    def main_phase(self, gs: GameState):
        if gs.turn == 1:
            self.reset_game()
        self.reset_turn()

        # 1. Land drop
        self._play_land_if_able(gs)

        # 2. Creatures — cheapest first, haste ones fire immediately
        for name in self.CREATURES:
            for card in list(gs.hand()):
                if card.name != name:
                    continue
                if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    continue
                gs.cast_spell(card)
                if name in self.HASTE_CREATURES:
                    card.summoning_sickness = False
                    card.tags.add(KWTag.HASTE)
                # Hook for archetype-specific ETB effects (e.g. Saga counters)
                self._after_creature_etb(gs, name, card)
                break

        # 3a. Cantrips — cast before burn so draws find more burn.
        # Each noncreature cast pumps prowess via the engine.
        self._cast_cantrips(gs)

        # 3b. Pre-combat burn — pumps prowess + damage face
        self._cast_burn(gs, pre_combat=True)

        # 4. Pump spell on biggest attacker
        self._try_pump(gs)

        # 5. Archetype-specific pre-combat hook (pre-combat tricks,
        # activated abilities, saga chapter skips, etc.)
        self._custom_precombat(gs)

    # ------------------------------------------------------------------
    # Main phase 2 (post-combat)
    # ------------------------------------------------------------------

    def main_phase2(self, gs: GameState):
        # Straight-damage burn first — we're no longer pumping prowess
        self._cast_burn(gs, pre_combat=False)

        # Any leftover mana: deploy more creatures for next turn
        for name in self.CREATURES:
            for card in list(gs.hand()):
                if card.name != name:
                    continue
                if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    continue
                gs.cast_spell(card)
                if name in self.HASTE_CREATURES:
                    card.summoning_sickness = False
                    card.tags.add(KWTag.HASTE)
                self._after_creature_etb(gs, name, card)
                break

        self._custom_postcombat(gs)

    # ------------------------------------------------------------------
    # Burn / pump helpers
    # ------------------------------------------------------------------

    def _cast_cantrips(self, gs: GameState):
        """Cast every CANTRIP_SPELL we can afford. Their draw/filter
        effects resolve via card_effects.SPELL_EFFECTS; the cast itself
        pumps prowess for same-turn combat attackers."""
        # Cap iterations so a misconfigured cost_reduction or a cantrip
        # that draws another cantrip cannot hang the engine. Real Standard
        # decks never chain >20 cantrips a turn.
        for _ in range(30):
            changed = False
            for name in self.CANTRIP_SPELLS:
                for card in list(gs.hand()):
                    if card.name != name:
                        continue
                    if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        continue
                    gs.cast_spell(card)
                    changed = True
                    break
                if changed:
                    break
            if not changed:
                return

    def _cast_burn(self, gs: GameState, pre_combat: bool):
        """Cast burn spells from BURN_SPELLS until we can't afford any.
        Pre-combat prefers cheap spells (more prowess triggers per mana);
        post-combat prefers high damage-per-mana."""
        if pre_combat:
            order = sorted(self.BURN_SPELLS.items(), key=lambda kv: kv[1][0])
        else:
            order = sorted(self.BURN_SPELLS.items(),
                           key=lambda kv: -(kv[1][1] / max(kv[1][0], 1)))
        for name, (cost, dmg) in order:
            for card in list(gs.hand()):
                if card.name != name:
                    continue
                if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    continue
                gs.cast_spell(card)
                gs.damage_dealt += dmg
                gs._log(f"  {name}: {dmg} damage to face "
                        f"({gs.damage_dealt} total)")
                break

    def _try_pump(self, gs: GameState):
        """Apply a pump spell (Monstrous Rage, etc.) to the biggest
        non-sick attacker. Capped to once per turn per self._pump_applied_this_turn."""
        if self._pump_applied_this_turn:
            return
        for name, (cost, boost, grants_trample) in self.PUMP_SPELLS.items():
            for card in list(gs.hand()):
                if card.name != name:
                    continue
                if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    continue
                target = self._pick_pump_target(gs)
                if target is None:
                    return
                gs.cast_spell(card)
                target.counters += boost
                if grants_trample and KWTag.TRAMPLE not in target.tags:
                    target.tags.add(KWTag.TRAMPLE)
                self._pump_applied_this_turn = True
                gs._log(f"  {name}: +{boost}/+0"
                        f"{' trample' if grants_trample else ''} "
                        f"on {target.name}")
                return

    def _pick_pump_target(self, gs: GameState):
        """Return the creature to pump. Default: non-sick + highest
        effective power. Subclasses can override to prefer prowess
        creatures, double-strikers, etc."""
        candidates = [
            c for c in gs.zones.creatures_on_battlefield()
            if not c.summoning_sickness or KWTag.HASTE in c.tags
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda c: _power_of(c), reverse=True)
        return candidates[0]

    # ------------------------------------------------------------------
    # Hooks — override in subclass for archetype-specific behavior
    # ------------------------------------------------------------------

    def _after_creature_etb(self, gs: GameState, name: str, card):
        """Called right after a creature/enchantment from CREATURES
        resolves. Default: no-op. Override to model ETB triggers
        (Kumano counter, Goddric exile check, etc.)."""
        pass

    def _custom_precombat(self, gs: GameState):
        """Extra pre-combat actions (saga activations, planeswalker
        abilities, ritual chains). Default: no-op."""
        pass

    def _custom_postcombat(self, gs: GameState):
        """Extra post-combat actions (card draw, recur effects,
        end-step cleanup). Default: no-op."""
        pass


# ──────────────────────────────────────────────────────────────────────
# Module helpers
# ──────────────────────────────────────────────────────────────────────

def _is_enchantment(card) -> bool:
    return "enchantment" in (getattr(card, "type_line", "") or "").lower()


def _power_of(card) -> int:
    try:
        return int(card.power or "0")
    except (ValueError, TypeError):
        return 0
