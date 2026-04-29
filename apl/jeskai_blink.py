"""apl/jeskai_blink.py — Jeskai Blink (Modern) goldfish APL.

Composes apl/card_specs/ for shared card logic. Skips dead-in-goldfish
cards (Solitude, Galvanic, Consign, Prismatic, March, Wrath — all need
opponent state to be useful).

Architecture:
  - Goldfish-only path. For matchup-aware play, see apl/jeskai_blink_match.py
    (595L hand-tuned with Phelia attack-trigger, Solitude evoke chain,
    Wrath, March pitch logic, Consign trigger counters, etc.)
  - Phlage / Ragavan / Phelia / Ephemerate logic lives in apl/card_specs/.
  - This APL is ~80 lines of orchestration over the spec primitives.

History:
  - 2026-04-26 Stage A: 24L GenericAPL shim (no goldfish kill logic).
  - 2026-04-28: hand-tuned port from match APL — made it WORSE in goldfish
    (T6.43 -> T7.51) because match-tuned keep+plays don't translate
    (~33% of deck is interaction, dead in goldfish). Reverted.
  - 2026-04-29: rebuilt as card_specs composition. Ports only the goldfish-
    viable plays: Ragavan (T1), Phelia (T2 + ETB blink target),
    Phlage hardcast (T3 reach), Phlage escape (T5+ finisher),
    Ephemerate (re-trigger ETB). Casey Jones / Quantum Riddler / Fable /
    Teferi inlined for now (Tier 2/3 extraction deferred to future spec).

Spec: harness/specs/2026-04-29-card-specs-framework.md
"""
from __future__ import annotations
from apl.base_apl import BaseAPL
from data.card import Card, Tag
from engine.game_state import GameState
from apl.card_specs import phlage, ragavan, phelia, ephemerate

# Inline-still cards (Tier 2/3 — pending extraction)
PHLAGE = "Phlage, Titan of Fire's Fury"
QUANTUM = "Quantum Riddler"
CASEY = "Casey Jones, Vigilante"
TEFERI = "Teferi, Time Raveler"
FABLE = "Fable of the Mirror-Breaker"

# Threats for keep() decisions
THREATS = {ragavan.NAME, phelia.NAME, QUANTUM, CASEY, PHLAGE}


class JeskaiBlinkAPL(BaseAPL):
    name = "Jeskai Blink"
    win_condition_damage = 20
    max_turns = 12

    def __init__(self):
        self._ephemerate_rebound = False
        self._casey_discard_pending = False

    # -------------------------------------------------------------------
    # Mulligan
    # -------------------------------------------------------------------
    def keep(self, hand, mulligans, on_play):
        """Goldfish keep: matches GenericAPL midrange leniency (2-4 lands +
        any cmc<=2 nonland) PLUS recognizes Phlage as always keep-worthy
        (its 3-mana hardcast = guaranteed 3 face dmg even if rest of hand
        is mediocre).

        Prior version was too strict (required 2 named THREATS) -> 0.64
        avg mulls vs SHIM 0.32 -> opening hand size penalty made kill
        clock SLOWER not faster.
        """
        if len(hand) <= 4:
            return True
        if mulligans >= 3:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands == 0:
            return False
        if lands >= 5 and len(hand) >= 6:
            return False
        spells = len(hand) - lands
        if spells == 0:
            return False

        # Snap keep: any hand with Phlage in hand (guaranteed reach)
        if any(c.name == PHLAGE for c in hand) and lands >= 2:
            return True
        # Standard midrange keep (matches GenericAPL leniency)
        has_early = any(getattr(c, 'cmc', 99) <= 2 for c in hand if not c.is_land())
        return 2 <= lands <= 4 and has_early

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        # Bottom: extra lands beyond 4, then highest-cmc dead-weight
        return (lands[4:] + spells)[:n]

    # -------------------------------------------------------------------
    # Main phase
    # -------------------------------------------------------------------
    def main_phase(self, gs: GameState):
        self._play_land(gs)
        gs.tap_lands()

        # Casey Jones discard 3 (deferred from prior turn's ETB)
        if self._casey_discard_pending:
            self._casey_discard_pending = False
            for _ in range(3):
                if gs.zones.hand:
                    worst = min(gs.zones.hand, key=self._card_value)
                    gs.zones.hand.remove(worst)
                    gs.zones.graveyard.append(worst)

        # Ephemerate rebound — free blink at upkeep
        if self._ephemerate_rebound:
            self._ephemerate_rebound = False
            ephemerate.fire_rebound(gs)

        # 1. Cheap creatures (T1-T2 curve)
        ragavan.cast(gs)
        phelia.cast(gs)

        # 2. Phlage: prefer escape > hardcast (escape = 6/6 finisher;
        #    hardcast = one-time 3 dmg + sac to GY)
        if not phlage.escape(gs):
            phlage.hardcast(gs)

        # 3. Casey Jones (3 mana) — draw 3 + defer discard 3
        for c in list(gs.zones.hand):
            if c.name == CASEY and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs.zones.draw(3)
                self._casey_discard_pending = True
                break

        # 4. Quantum Riddler (5 mana) — 4/6 flying + draw 1
        for c in list(gs.zones.hand):
            if c.name == QUANTUM and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs.zones.draw(1)
                break

        # 5. Teferi (3 mana) — -3 for draw (bounce target dead in goldfish)
        for c in list(gs.zones.hand):
            if c.name == TEFERI and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs.zones.draw(1)
                break

        # 6. Fable (3 mana saga) — Ch1 loot
        for c in list(gs.zones.hand):
            if c.name == FABLE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                if gs.zones.hand:
                    worst = min(gs.zones.hand, key=self._card_value)
                    gs.zones.hand.remove(worst)
                    gs.zones.graveyard.append(worst)
                    gs.zones.draw(1)
                break

        # 7. Ephemerate — blink best ETB on board (re-trigger value)
        rebound_cb = lambda: setattr(self, '_ephemerate_rebound', True)
        ephemerate.cast(gs, rebound_flag_setter=rebound_cb)

        # 8. Fill remaining mana with any leftover creatures
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and c.name not in {PHLAGE}:
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)

    def main_phase2(self, gs: GameState):
        # Post-combat: any plays missed pre-combat (e.g., Phlage escape after
        # combat damage filled GY with sacrificed attackers)
        self.main_phase(gs)

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------
    def _card_value(self, c: Card) -> int:
        """Rate card value for discard decisions (Casey upkeep, Fable loot)."""
        if c.is_land():       return 1
        if c.name == phelia.NAME:   return 9
        if c.name == PHLAGE:        return 7
        if c.name == QUANTUM:       return 7
        if c.name == ragavan.NAME:  return 5
        if c.name == ephemerate.NAME: return 8
        return 3

    def _play_land(self, gs: GameState):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        # Prefer fetches > Arena of Glory > shocks > basics
        def score(c: Card) -> int:
            name = (c.name or "").lower()
            if any(k in name for k in ("strand", "mesa", "tarn")):
                return 0
            if "arena" in name:
                return 1
            if any(k in name for k in ("vents", "foundry", "fountain")):
                return 2
            return 3
        gs.play_land(min(lands, key=score))
