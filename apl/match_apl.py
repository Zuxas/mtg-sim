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
    MatchGameState, optimal_blocking, safe_power, safe_toughness, has_keyword
)
from data.card import Card, Tag


class MatchAPL(BaseAPL):
    """
    Extended APL interface for two-player games.
    Inherits keep/bottom from BaseAPL, adds opponent-aware methods.
    """

    # Deck-level override: set True for tribal / token / go-wide
    # decks whose plan is 'attack with everyone' regardless of trade
    # math. Lord pumps (Merfolk, Slivers, Humans), anthem effects
    # (Intangible Virtue), and token generators (Bitterblossom
    # archetypes) benefit — their creatures trade or chip through
    # collectively even when individual attacks look bad.
    ATTACK_ALL_IN = False

    # R1 priority-stack opt-in gate (design 1.5). Default OFF so every
    # existing deck keeps the legacy synchronous counter window and stays
    # bit-identical. Interaction-capable subclasses (AwareMatchAPL) flip
    # this True to route casts through the real on-stack LIFO priority loop.
    WANTS_PRIORITY_STACK = False

    # R2 instant-speed combat opt-in gate (design 1.5). Default OFF so every
    # existing deck keeps the legacy shallow combat hooks and the gate-OFF
    # combat path stays byte-identical. The single tempo APL that flips this
    # True (MurktideMatchAPL) routes the two combat windows (post-attackers,
    # post-blockers) through the SHARED engine.priority_stack.run_priority_pass
    # core. When OFF, _instant_combat_enabled returns False on both runners and
    # none of the R2 window code is reached.
    WANTS_INSTANT_COMBAT = False

    def priority_action(self, my_gs, opp_gs, stack):
        """R1 priority hook: respond to the current top of `stack`.

        Returns (counter_card, target_uid) to cast a counter, or None to pass.
        Base implementation always passes, so every non-opted-in deck is inert
        in run_priority_stack (and the gate is OFF for it anyway). Subclasses
        that set WANTS_PRIORITY_STACK = True override this.
        """
        return None

    def combat_priority_action(self, my_gs, their_gs, stack, window):
        """R2 combat priority hook: respond inside a gated combat window.

        `window` is 1 (after attackers declared, before blockers) or 2 (after
        blockers declared, before combat damage). Returns (card, target) to
        cast an instant at this priority, or None to pass.

        Base implementation always passes, so every non-opted-in deck is a
        no-op inside the combat window (and the gate is OFF for it anyway).
        The single tempo subclass that sets WANTS_INSTANT_COMBAT = True
        overrides this (design 1.5).
        """
        return None

    # Archetype category for sideboard-plan matching. One of:
    #   'aggro', 'midrange', 'control', 'combo', 'ramp', 'tempo'.
    # Used as a key into the opponent's SB_PLANS dict.
    ARCHETYPE = "midrange"

    # Sideboard plans keyed by opponent ARCHETYPE string. Each value
    # is a (sb_in_lines, sb_out_lines) tuple of Arena-format strings
    # understood by engine.sideboard.apply_sideboard_plan:
    #   'N Card Name'
    # An empty or missing entry means no sideboarding for that matchup.
    #
    # Example (Jeskai Control vs Aggro):
    #   SB_PLANS = {
    #       'aggro': (
    #           ['2 Torch the Tower', '2 Abrade'],
    #           ['2 Three Steps Ahead', '2 Stock Up'],
    #       ),
    #   }
    SB_PLANS: dict = {}

    def sb_plan_for(self, opp_archetype: str):
        """Return (sb_in_raw, sb_out_raw) tuple or None. Consumed by
        engine.bo3_match.run_bo3 before game 2 / 3."""
        plan = self.SB_PLANS.get(opp_archetype)
        if not plan:
            return None
        sb_in, sb_out = plan
        return (list(sb_in), list(sb_out))

    # Removal spells that actually kill a creature in match mode.
    # Keyed by card name → (cmc_cost, kills_any_tougher_than). The
    # second value is the maximum toughness the spell can handle
    # (None = unconditional). Overrides the goldfish SPELL_EFFECTS
    # path which only adds face damage.
    MATCH_REMOVAL = {
        # Jeskai
        "Lightning Helix":  (2, 3),    # 3 dmg → kills toughness ≤ 3
        "Get Lost":         (2, None), # exile any nonland permanent
        # Seam Rip exiles ENCHANTMENT only — not a creature answer,
        # intentionally omitted. Same for Abandon Attachments.
        "Fire Magic":       (1, 2),    # 1-mode deals 2 dmg
        # Dimir / black
        "Bitter Triumph":   (2, None), # any creature/planeswalker
        "Shoot the Sheriff":(2, 3),
        "Long Goodbye":     (2, None), # any non-legendary
        "Go for the Throat":(2, None), # non-artifact creature
        "Requiting Hex":    (1, 2),    # destroy creature CMC ≤ 2
        "Deadly Cover-Up":  (5, None), # wrath, evidence=6 names a card
        "Archenemy's Charm":(3, None), # exile creature/PW mode
        # Azorius / white
        "Day of Judgment":  (4, None), # board wipe
        "Depopulate":       (4, None),
        "Sunfall":          (5, None),
        "Farewell":         (6, None),
        "Temporary Lockdown":(3, 2),
        # Standard burn
        "Lightning Strike": (2, 3),
        "Burst Lightning":  (1, 2),
        "Shock":            (1, 2),
        "Torch the Tower":  (1, 2),
        "Obliterating Bolt":(3, 3),
        "Abrade":           (2, 3),
        "Witchstalker Frenzy":(2, 4),
        # Other
        "Exorcise":         (3, None), # exile tapped creature/PW
        "Stab":             (1, 2),    # -2/-2
        # Izzet Lesson / Spellementals creature answers
        # Intentionally NOT listed here:
        #   - Firebending Lesson (saga making 1/1 tokens, not reliable
        #     removal; the level-3 chapter can damage but we already
        #     handle its cast via SAGA_EFFECTS)
        #   - It'll Quench Ya (card draw, not removal)
        #   - Abandon Attachments (artifact/enchant hate, not creature)
        "Combustion Technique":(2, 2), # deal 2 to creature/PW
        "Iroh's Demonstration":(3, 3), # -3/-3 creature debuff
        "Sear":             (2, 3),    # 3 dmg bolt
        "Pyroclasm":        (2, 2),    # 2 dmg to each
        "Slagstorm":        (3, 3),    # 3 dmg each (or player)
        # Gruul / prowess
        "Scorching Shot":   (2, 4),
        # Ramp extras
        "Destroy Evil":     (2, None),
        "Path of Peril":    (3, 2),    # 2 dmg each (tiered)
        "The Cruelty of Gix":(5, None),
        # Dimir extras
        "Faebloom Trick":   (3, 3),    # exile face-up creature
        "Annul":            (1, None), # counter artifact/enchant
        "Strategic Betrayal":(3, None),
    }

    # Spells that are AoE wipes (affect whole board, not just target).
    MATCH_WIPES = {"Day of Judgment", "Depopulate", "Sunfall",
                   "Farewell", "Temporary Lockdown", "Pyroclasm",
                   "Slagstorm", "Path of Peril", "Deadly Cover-Up"}
    MATCH_EXILE = {"Sunfall", "Farewell", "Get Lost", "Seam Rip",
                   "Exorcise", "Faebloom Trick"}

    def _match_cast_removal(self, gs: GameState, opponent: GameState):
        """Before anything else, if we have a removal spell in hand and
        opp has a threatening creature, kill it. Fires at the top of
        main_phase_match so reactive removal doesn't rot when the APL
        calls main_phase2 and dumps leftovers at opp's face."""
        if opponent is None:
            return
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures:
            return
        # Sort biggest first — we want to answer the real threat
        targets = sorted(opp_creatures,
                         key=lambda c: -safe_power(c))
        for target in targets:
            if safe_power(target) < 1:
                continue
            cast_any = False
            for card in list(gs.zones.hand):
                spec = self.MATCH_REMOVAL.get(card.name)
                if not spec:
                    continue
                _cost, max_tgh = spec
                if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    continue
                # Can this spell actually kill the target?
                if max_tgh is not None and safe_toughness(target) > max_tgh:
                    continue
                # Pay and resolve — skip SPELL_EFFECTS face-damage path.
                gs.mana_pool.pay(card.mana_cost, card.cmc)
                gs.zones.hand.remove(card)
                gs.zones.graveyard.append(card)
                gs.noncreature_spells_this_turn += 1
                # Wipes affect the whole board. AoE wipes (Pyroclasm,
                # Slagstorm, Path of Peril) only kill creatures with
                # toughness ≤ the damage dealt — max_tgh already
                # captures that threshold.
                if card.name in self.MATCH_WIPES:
                    exile_mode = card.name in self.MATCH_EXILE
                    killed = 0
                    for cr in list(opponent.zones.battlefield):
                        if not (cr.has(Tag.CREATURE) and not cr.is_land()):
                            continue
                        if max_tgh is not None and safe_toughness(cr) > max_tgh:
                            continue
                        opponent.zones.battlefield.remove(cr)
                        if exile_mode:
                            opponent.zones.exile.append(cr)
                        else:
                            opponent.zones.graveyard.append(cr)
                        killed += 1
                    gs._log(f"  {card.name}: kill {killed} opp creatures")
                    return  # wipe resolves whole board, stop
                else:
                    # Spot removal
                    opponent.zones.battlefield.remove(target)
                    if card.name in self.MATCH_EXILE:
                        opponent.zones.exile.append(target)
                    else:
                        opponent.zones.graveyard.append(target)
                    gs._log(f"  {card.name} -> kill {target.name}")
                cast_any = True
                break
            if cast_any:
                # Only one removal per turn from this helper — main
                # loop still has main_phase2 for leftover reactive
                # spells (they'll go face per SPELL_EFFECTS).
                return

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """
        Main phase with opponent awareness.
        Default: falls back to goldfish main_phase but stashes the
        opponent GS on self so base-class hooks (ControlAPL's
        _should_wipe, AggroAPL's _should_hold_threat, etc.) can
        consult the opp board when deciding plays.

        Composed control/ramp APLs split decisions across main_phase
        (pre-combat, reserves reactive mana) and main_phase2 (releases
        unused reactive mana into removal / second threats / wipes).
        Match mode has a single combat step before end-of-turn, so we
        run both halves here to give control decks their full mana.

        Order:
          1. _match_cast_removal (kill a threat if possible)
          2. main_phase (goldfish proactive plays)
          3. main_phase2 (goldfish reactive dump)
        """
        self._opp_gs = opponent
        # Set gs._match_opp so all ETB/spell handlers can find the opponent.
        # Handlers read this attribute; without it they no-op and silently skip removal.
        if opponent is not None:
            gs._match_opp = opponent
        self._match_cast_removal(gs, opponent)
        self.main_phase(gs)
        if hasattr(self, "main_phase2"):
            try:
                self.main_phase2(gs)
            except Exception:
                pass

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

        Real-Magic heuristic:
          - Always attack with creatures opp can't block (evasion:
            flying vs no-flying-blockers, or nothing at all on opp's
            side). These trade up / hit face for free.
          - Attack with creatures that WILL die to blocks ONLY when
            the race math says yes (we're ahead on damage OR opp's
            next draw can kill us — we need to push through).
          - Otherwise hold back small creatures against bigger
            blockers.

        Subclasses can override for deck-specific logic (go-wide
        decks want everyone swinging even into unfavorable blocks
        because of Lord pumps / token synergies).
        """
        from engine.keywords import KWTag
        eligible = [c for c in gs.zones.battlefield
                    if not c.is_land()
                    and not getattr(c, 'summoning_sickness', False)
                    and not getattr(c, 'tapped', False)]
        if not eligible:
            return []

        # Go-wide opt-in: tribal / token / Lord decks just attack.
        if self.ATTACK_ALL_IN:
            return eligible

        # Blockers opp has on the table
        opp_blockers = [c for c in opponent.zones.battlefield
                        if not c.is_land()
                        and not getattr(c, 'tapped', False)]

        # If opp has no blockers, attack with everything — free damage.
        if not opp_blockers:
            return eligible

        # Race math: our damage so far + likely future = opp's life-ish.
        # If we're ahead on damage OR nearly lethal, push — even into
        # unfavorable trades. Threshold: opp_damage < my_damage or
        # my_damage >= 14 (close enough to lethal to justify risk).
        my_dmg = getattr(gs, "damage_dealt", 0)
        opp_dmg = self._opp_damage_dealt()
        push_through = (my_dmg > opp_dmg) or (my_dmg >= 14)

        # Count how many more cards we have in hand that could pump
        # attackers (prowess trigger from noncreature spells, etc.).
        # If we've got 2+ spells sitting in hand, our creatures will
        # hit harder during damage step than they look right now.
        pump_potential = sum(
            1 for c in gs.hand()
            if not c.is_land() and not c.has(Tag.CREATURE)
        )

        attackers = []
        for atk in eligible:
            atk_power = safe_power(atk)
            atk_tough = safe_toughness(atk)
            has_prowess = KWTag.PROWESS in atk.tags

            # Evasion: flying hits face if no flying/reach blocker
            atk_flying = KWTag.FLYING in atk.tags
            flying_blockers_exist = any(
                KWTag.FLYING in b.tags or KWTag.REACH in b.tags
                for b in opp_blockers
            )
            if atk_flying and not flying_blockers_exist:
                attackers.append(atk)
                continue

            # Prowess creatures effectively get +pump_potential/+0 this
            # turn from their controller's noncreature spells. Bake
            # that into the trade math.
            effective_power = atk_power + (pump_potential if has_prowess else 0)
            effective_tough = atk_tough + (pump_potential if has_prowess else 0)

            # Find the smallest blocker that could kill this attacker
            # (power >= atk_tough after pump). If all blockers would
            # die in the trade or the attacker survives, attack.
            trades_well = False
            dies_alone = False
            for blk in opp_blockers:
                blk_power = safe_power(blk)
                blk_tough = safe_toughness(blk)
                if blk_power >= effective_tough:
                    if effective_power >= blk_tough:
                        trades_well = True
                    else:
                        dies_alone = True
                    break

            if trades_well or push_through:
                attackers.append(atk)
                continue
            if not dies_alone:
                attackers.append(atk)

        return attackers

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


class RemovalAwareGoldfishAdapter(MatchAPL):
    """
    Wraps a goldfish BaseAPL so that MatchAPL._match_cast_removal fires
    at the opponent's creatures BEFORE the inner goldfish main_phase
    runs. Unlike the basic GoldfishAdapter which short-circuits past
    the removal path entirely, this adapter invokes MatchAPL's real
    sequence: _match_cast_removal → inner.main_phase → inner.main_phase2.

    Used by match_runner._simple_play_turn to auto-upgrade any
    registered goldfish APL to opponent-aware removal play without
    forcing every deck to have a hand-tuned MatchAPL subclass. Landed
    2026-04-24 after Gate B showed goldfish-only main_phase scored
    control decks at 0% vs aggro because removal never fired.

    Known limitations (below the MVP's accepted line):
    - Combat is still heuristic (handled by match_runner._resolve_combat)
    - declare_attackers / declare_blockers not invoked
    - counters, combat tricks, EOT actions not invoked
    """

    def __init__(self, inner: BaseAPL):
        self.inner = inner
        self.name = getattr(inner, "name", inner.__class__.__name__)

    def keep(self, hand, mulligans, on_play) -> bool:
        return self.inner.keep(hand, mulligans, on_play)

    def bottom(self, hand, n) -> list:
        return self.inner.bottom(hand, n)

    def main_phase(self, gs: GameState):
        self.inner.main_phase(gs)

    def main_phase2(self, gs: GameState):
        if hasattr(self.inner, "main_phase2"):
            self.inner.main_phase2(gs)

    # main_phase_match is inherited from MatchAPL. It calls:
    #   self._opp_gs = opponent
    #   self._match_cast_removal(gs, opponent)  # uses MATCH_REMOVAL dict
    #   self.main_phase(gs)                     # delegates to inner
    #   self.main_phase2(gs)                    # delegates


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
