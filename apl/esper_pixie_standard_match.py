"""
apl/esper_pixie_standard_match.py — Esper Pixie match APL (Standard 2026)

Alex Sanchez list (2nd place Sunday ReCQ). Flying tempo/blink deck.

Game plan:
  T1:  Nurturing Pixie or Spyglass Siren — 1/1 flyers, start the clock
  T2:  Stormchaser's Talent or Nowhere to Run (flash removal)
  T3:  Cosmogrand Zenith (2nd-spell token/pump trigger) or Sunpearl Kirin
  T4+: Kaito Bane of Nightmares, Momentum Breaker, Cryogen Relic draw

Key interactions:
  Void: Tragic Trajectory is -2/-2 normally, -10/-10 if a permanent left
    the battlefield this turn. Engine: sacrifice Cryogen Relic (draws a card)
    → Void active → Trajectory kills any creature.
  Blink loop: Nurturing Pixie ETB → bounce Sunpearl Kirin → Pixie gets +1/+1
    → replay Kirin (flash) → Kirin ETB bounces something else. Builds board.
  Cosmogrand Zenith: 2nd spell each turn → 2 1/1 Soldiers OR pump all creatures.
  Nowhere to Run: flash -3/-3. Also enables Void when it bounces (leaves BF).
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from engine.match_state import safe_power, safe_toughness
from apl.aware_match_apl import AwareMatchAPL, BLINK_BAIT

NURTURING_PIXIE   = "Nurturing Pixie"
SPYGLASS_SIREN    = "Spyglass Siren"
SUNPEARL_KIRIN    = "Sunpearl Kirin"
COSMOGRAND_ZENITH = "Cosmogrand Zenith"
KAITO             = "Kaito, Bane of Nightmares"
MOMENTUM_BREAKER  = "Momentum Breaker"
CRYOGEN_RELIC     = "Cryogen Relic"
STORMCHASERS      = "Stormchaser's Talent"
TINYBONES         = "Tinybones Joins Up"
NOWHERE_TO_RUN    = "Nowhere to Run"
TRAGIC_TRAJECTORY = "Tragic Trajectory"

ANNUL        = "Annul"
DURESS       = "Duress"
EXORCISE     = "Exorcise"
GHOST_VACUUM = "Ghost Vacuum"
NO_MORE_LIES = "No More Lies"
SEAM_RIP     = "Seam Rip"
STOCK_UP     = "Stock Up"


class EsperPixieMatchAPL(AwareMatchAPL):
    name = "Esper Pixie"
    ARCHETYPE = "tempo"

    COUNTER_COST  = 2    # hold {1}{B} for Nowhere to Run (flash)
    COUNTER_CARDS = set()

    MATCH_REMOVAL = {
        NOWHERE_TO_RUN:    ("1B", 3),
        TRAGIC_TRAJECTORY: ("B",  2),
    }
    MATCH_EXILE = set()
    MATCH_BOUNCE = set()
    MATCH_WIPES  = set()

    SB_PLANS = {
        "aggro": (
            [ANNUL, ANNUL, SEAM_RIP, SEAM_RIP, EXORCISE, EXORCISE],
            [KAITO, KAITO, KAITO, TINYBONES, TINYBONES, CRYOGEN_RELIC],
        ),
        "control": (
            [DURESS, DURESS, NO_MORE_LIES, NO_MORE_LIES, STOCK_UP, STOCK_UP],
            [MOMENTUM_BREAKER, MOMENTUM_BREAKER, NOWHERE_TO_RUN,
             TRAGIC_TRAJECTORY, TRAGIC_TRAJECTORY, TINYBONES],
        ),
        "combo": (
            [DURESS, DURESS, NO_MORE_LIES, NO_MORE_LIES, GHOST_VACUUM, GHOST_VACUUM],
            [MOMENTUM_BREAKER, MOMENTUM_BREAKER, CRYOGEN_RELIC, CRYOGEN_RELIC,
             TINYBONES, TINYBONES],
        ),
        "ramp": (
            [ANNUL, ANNUL, EXORCISE, EXORCISE, DURESS, DURESS],
            [KAITO, KAITO, TINYBONES, TINYBONES, CRYOGEN_RELIC, CRYOGEN_RELIC],
        ),
        "tempo": (
            [NO_MORE_LIES, NO_MORE_LIES, ANNUL, ANNUL, SEAM_RIP, SEAM_RIP],
            [MOMENTUM_BREAKER, MOMENTUM_BREAKER, TINYBONES, TINYBONES,
             COSMOGRAND_ZENITH, COSMOGRAND_ZENITH],
        ),
    }

    # ── Mulligan ─────────────────────────────────────────────────────────────

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands < 2 or lands > 5:
            return False
        has_flyer    = any(c.name in {NURTURING_PIXIE, SPYGLASS_SIREN, SUNPEARL_KIRIN}
                           for c in hand)
        has_removal  = any(c.name in {NOWHERE_TO_RUN, TRAGIC_TRAJECTORY, MOMENTUM_BREAKER}
                           for c in hand)
        if has_flyer and lands >= 2:
            return True
        if has_flyer and has_removal:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands  = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        filler = sorted(
            [c for c in hand if not c.is_land()
             and c.name not in {NURTURING_PIXIE, SPYGLASS_SIREN, NOWHERE_TO_RUN,
                                 TRAGIC_TRAJECTORY, SUNPEARL_KIRIN}],
            key=lambda c: -getattr(c, 'cmc', 0)
        )
        return (lands[3:] + filler)[:n]

    # ── Mana reserve ─────────────────────────────────────────────────────────

    def reserve_mana(self, gs: GameState, opponent: GameState):
        has_ntrun = any(c.name == NOWHERE_TO_RUN for c in gs.zones.hand)
        gs.mana_reserve = 2 if has_ntrun else 0

    # ── Void helper ───────────────────────────────────────────────────────────

    def _void_active(self, gs: GameState) -> bool:
        return getattr(gs, '_void_enabled_this_turn', False)

    def _try_enable_void(self, gs: GameState) -> bool:
        """Sacrifice Cryogen Relic: draw a card, enable Void for this turn."""
        relic = next((c for c in gs.zones.battlefield if c.name == CRYOGEN_RELIC), None)
        if relic is None or not gs.mana_pool.can_cast("{1}{U}", 2):
            return False
        gs.mana_pool.pay("{1}{U}", 2)
        gs.zones.battlefield.remove(relic)
        gs.zones.graveyard.append(relic)
        if gs.zones.library:
            gs.zones.hand.append(gs.zones.library.pop(0))
        gs._void_enabled_this_turn = True
        gs._log("  Cryogen Relic: sacrificed -> Void enabled, drew 1")
        return True

    # ── Removal (Void-aware) ──────────────────────────────────────────────────

    def _kill_target(self, gs: GameState, opponent: GameState, target) -> bool:
        tou = safe_toughness(target)

        # Tragic Trajectory first (cheaper {B})
        traj = next((c for c in gs.zones.hand if c.name == TRAGIC_TRAJECTORY), None)
        if traj and gs.mana_pool.can_cast(traj.mana_cost, traj.cmc):
            if tou > 2 and not self._void_active(gs):
                self._try_enable_void(gs)
            if tou <= 2 or self._void_active(gs):
                gs.mana_pool.pay(traj.mana_cost, traj.cmc)
                gs.zones.hand.remove(traj)
                gs.zones.graveyard.append(traj)
                gs.noncreature_spells_this_turn += 1
                if target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.graveyard.append(target)
                gs._log(f"  Tragic Trajectory ({'Void -10' if self._void_active(gs) else '-2'}): "
                        f"kills {target.name}")
                return True

        # Nowhere to Run (-3/-3, or -10/-10 with Void)
        ntrun = next((c for c in gs.zones.hand if c.name == NOWHERE_TO_RUN), None)
        if ntrun and gs.mana_pool.can_cast(ntrun.mana_cost, ntrun.cmc):
            if tou > 3 and not self._void_active(gs):
                self._try_enable_void(gs)
            if tou <= 3 or self._void_active(gs):
                gs.mana_pool.pay(ntrun.mana_cost, ntrun.cmc)
                gs.zones.hand.remove(ntrun)
                gs.zones.graveyard.append(ntrun)
                gs.noncreature_spells_this_turn += 1
                if target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.graveyard.append(target)
                gs._log(f"  Nowhere to Run ({'Void -10' if self._void_active(gs) else '-3'}): "
                        f"kills {target.name}")
                return True

        return False

    # ── Pre-combat instant ────────────────────────────────────────────────────

    def pre_combat_instant(self, gs: GameState, opponent: GameState):
        gs._void_enabled_this_turn = getattr(gs, '_void_enabled_this_turn', False)
        opp_threats = sorted(
            [c for c in opponent.zones.battlefield
             if c.has(Tag.CREATURE) and not c.is_land()],
            key=lambda c: -safe_power(c)
        )
        for target in opp_threats:
            if safe_power(target) >= 3 or target.name in BLINK_BAIT:
                if self._kill_target(gs, opponent, target):
                    return
        super().pre_combat_instant(gs, opponent)

    # ── Main phase ────────────────────────────────────────────────────────────

    def main_phase_match(self, gs: GameState, opponent: GameState):
        self._opp_gs = opponent
        gs._void_enabled_this_turn = False

        self._play_land_if_able(gs)
        self.reserve_mana(gs, opponent)
        gs.tap_lands()

        # Kill biggest threat if removal available
        opp_creatures = sorted(
            [c for c in (opponent.zones.battlefield if opponent else [])
             if c.has(Tag.CREATURE) and not c.is_land()],
            key=lambda c: -safe_power(c)
        )
        for target in opp_creatures:
            if safe_power(target) >= 2:
                if self._kill_target(gs, opponent, target):
                    break

        # Stormchaser's Talent {U} — makes prowess Otter, cheap engine piece
        for c in list(gs.zones.hand):
            if c.name == STORMCHASERS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 1-drop flyers — Nurturing Pixie, Spyglass Siren
        for c in list(gs.zones.hand):
            if c.name in {NURTURING_PIXIE, SPYGLASS_SIREN}:
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)

        # Tinybones Joins Up — {B} discard/mill engine
        for c in list(gs.zones.hand):
            if c.name == TINYBONES and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Cosmogrand Zenith after 1+ spells this turn to trigger 2nd-spell ability
        if gs.noncreature_spells_this_turn >= 1 or gs.spells_cast_this_turn >= 1:
            for c in list(gs.zones.hand):
                if c.name == COSMOGRAND_ZENITH and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # Sunpearl Kirin {1}{W} flash — ETB returns a permanent to hand
        for c in list(gs.zones.hand):
            if c.name == SUNPEARL_KIRIN and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Momentum Breaker — ETB each opp sacrifices; better when they have a board
        if opponent and any(c.has(Tag.CREATURE) and not c.is_land()
                            for c in opponent.zones.battlefield):
            for c in list(gs.zones.hand):
                if c.name == MOMENTUM_BREAKER and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # Cryogen Relic — hold if we have Tragic Trajectory (sacrifice for Void later)
        if not any(c.name == TRAGIC_TRAJECTORY for c in gs.zones.hand):
            for c in list(gs.zones.hand):
                if c.name == CRYOGEN_RELIC and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # Kaito — deploy normally (ninjutsu not modeled in goldfish engine)
        for c in list(gs.zones.hand):
            if c.name == KAITO and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Cosmogrand Zenith fallback if not cast above
        for c in list(gs.zones.hand):
            if c.name == COSMOGRAND_ZENITH and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

    def main_phase(self, gs: GameState):
        self.main_phase_match(gs, None)

    # ── Combat ────────────────────────────────────────────────────────────────

    def declare_attackers(self, gs: GameState, opponent: GameState):
        """All flyers attack always. Non-flyers only if opponent board is clear."""
        attackers = []
        opp_bf = opponent.zones.battlefield if opponent else []
        opp_creatures = [c for c in opp_bf if c.has(Tag.CREATURE) and not c.is_land()
                         and not getattr(c, 'tapped', False)]
        for c in gs.zones.battlefield:
            if c.is_land() or not c.has(Tag.CREATURE): continue
            if getattr(c, 'summoning_sickness', False): continue
            if getattr(c, 'tapped', False): continue
            oracle = (getattr(c, 'oracle_text', '') or '').lower()
            is_flying = 'flying' in oracle
            if is_flying:
                attackers.append(c)
            elif not opp_creatures:
                attackers.append(c)
        return attackers

    def declare_blockers(self, gs: GameState, opp, attackers):
        """Block flying attackers with our flying creatures when favorable."""
        if not attackers:
            return {}
        assignments = {}
        my_flyers = [c for c in gs.zones.battlefield
                     if c.has(Tag.CREATURE) and not c.is_land()
                     and not getattr(c, 'tapped', False)
                     and 'flying' in (getattr(c, 'oracle_text', '') or '').lower()]
        used = set()
        for atk in sorted(attackers, key=lambda c: -safe_power(c)):
            atk_flying = 'flying' in (getattr(atk, 'oracle_text', '') or '').lower()
            if not atk_flying:
                continue
            available = [b for b in my_flyers if id(b) not in used]
            if not available:
                break
            best = max(available, key=lambda b: safe_toughness(b))
            if safe_toughness(best) > safe_power(atk):
                assignments[id(atk)] = [best]
                used.add(id(best))
        return assignments
