"""
apl/izzet_prowess_match.py — Match-aware Izzet Prowess APL (Modern)

Key differences from goldfish APL:
1. Cori-Steel Cutter modeled as EQUIPMENT (not creature) with Flurry
2. Slickshot Show-Off has PLOT mechanic (exile for free cast later)
3. BURST TURN logic: accumulate spells, release all in one combat
4. Mutagenic Growth held as COMBAT TRICK (cast after blockers)
5. Bolt/Dart target opponent CREATURES when profitable, face when racing
6. vs Boros: higher burst threshold (lifegain demands one-shot kills)

Card corrections from goldfish APL:
- Cori-Steel Cutter: {1}{R} Artifact — Equipment. Equipped creature gets
  +1/+1, trample, haste. Flurry: 2nd spell each turn → 1/1 Monk with prowess,
  may attach Cori-Steel to it.
- Slickshot Show-Off: {1}{R} 3/1 flying haste prowess. Plot {1}{R}.
  When plotted, cast for free on a later turn with haste.
"""

from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness, has_keyword
from engine.stack import classify_card, InteractionType, get_burn_damage

# Card names
SWIFTSPEAR = "Monastery Swiftspear"
DRC        = "Dragon's Rage Channeler"
SLICKSHOT  = "Slickshot Show-Off"
CORI       = "Cori-Steel Cutter"
BOLT       = "Lightning Bolt"
LAVA_DART  = "Lava Dart"
ITERATION  = "Expressive Iteration"
PREORDAIN  = "Preordain"
BAUBLE     = "Mishra's Bauble"
MUTAGENIC  = "Mutagenic Growth"
VIOLENT    = "Violent Urge"
UNHOLY     = "Unholy Heat"

# Creatures with prowess (NOT Cori-Steel — that's equipment)
PROWESS_CREATURES = {SWIFTSPEAR, SLICKSHOT, DRC}
# Note: Monk tokens from Cori-Steel also have prowess

# Cards that are noncreature spells (trigger prowess)
NONCREATURE_SPELLS = {BOLT, LAVA_DART, ITERATION, PREORDAIN, BAUBLE,
                      MUTAGENIC, VIOLENT, UNHOLY, CORI}

# Free spells (0 mana or alternate cost)
FREE_SPELLS = {BAUBLE, MUTAGENIC}  # Mutagenic = 2 life


class IzzetProwessMatchAPL(MatchAPL):
    name = "Izzet Prowess"
    win_condition_damage = 20
    max_turns = 10

    def __init__(self):
        # Per-game state
        self._plotted_cards = []       # cards in exile (plotted)
        self._spells_this_turn = 0     # for Flurry tracking
        self._prowess_boosts = []      # temporary counters to remove EOT
        self._cori_on_battlefield = False
        self._monks_created = 0

    def _reset_turn(self):
        self._spells_this_turn = 0
        self._prowess_boosts = []

    # ------------------------------------------------------------------
    # Mulligan logic
    # ------------------------------------------------------------------

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand
                      if c.name in PROWESS_CREATURES or c.name == DRC)
        fuel = sum(1 for c in hand
                   if c.name in NONCREATURE_SPELLS)
        if lands == 0:
            return False
        if threats == 0 and mulligans < 2:
            return False
        if lands == 1 and threats >= 1 and fuel >= 1:
            return True
        if lands >= 2 and threats >= 1:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        to_bottom = []
        if len(lands) > 2:
            to_bottom.extend(lands[2:])
        for c in spells:
            if len(to_bottom) >= n:
                break
            if c not in to_bottom:
                to_bottom.append(c)
        return to_bottom[:n]

    # ------------------------------------------------------------------
    # Burst damage calculator — "can I kill this turn?"
    # ------------------------------------------------------------------

    def _count_prowess_on_board(self, gs: GameState) -> int:
        """Count creatures with prowess currently on the battlefield."""
        count = 0
        for c in gs.zones.battlefield:
            if c.is_land():
                continue
            if c.name in PROWESS_CREATURES:
                if not getattr(c, 'summoning_sickness', False):
                    count += 1
            # Monk tokens from Cori-Steel have prowess
            if 'Monk' in c.name and 'Token' in c.name:
                if not getattr(c, 'summoning_sickness', False):
                    count += 1
        return count

    def _count_noncreature_fuel(self, gs: GameState) -> int:
        """Count castable noncreature spells in hand (prowess triggers)."""
        count = 0
        for c in gs.zones.hand:
            if c.name in FREE_SPELLS:
                count += 1
            elif c.name in NONCREATURE_SPELLS:
                if hasattr(c, 'cmc') and c.cmc <= gs.mana_pool.total():
                    count += 1
        # Lava Dart flashback from GY
        if any(c.name == LAVA_DART for c in gs.zones.graveyard):
            mountains = [c for c in gs.zones.battlefield
                         if 'mountain' in (c.type_line or '').lower() and not c.tapped]
            if mountains:
                count += 1
        return count

    def _calc_burst_damage(self, gs: GameState) -> int:
        """
        Calculate maximum damage if we chain all spells this turn.
        This is the combo kill calculation.
        """
        prowess_creatures = self._count_prowess_on_board(gs)
        fuel = self._count_noncreature_fuel(gs)

        # Base power of each attacking creature
        base_power = 0
        for c in gs.zones.battlefield:
            if c.is_land():
                continue
            if getattr(c, 'summoning_sickness', False):
                continue
            base_power += safe_power(c)

        # Plotted Slickshot adds 3 power (haste, can attack immediately)
        plotted_slickshots = sum(1 for c in self._plotted_cards if c.name == SLICKSHOT)
        if plotted_slickshots:
            base_power += 3 * plotted_slickshots
            prowess_creatures += plotted_slickshots

        # Each noncreature spell gives +1 to every prowess creature
        prowess_damage = fuel * prowess_creatures

        # Mutagenic Growth gives +2/+2 to one creature ON TOP of prowess
        has_mutagenic = any(c.name == MUTAGENIC for c in gs.zones.hand)
        mutagenic_bonus = 2 if has_mutagenic else 0

        # Direct damage from burn spells
        burn_damage = 0
        for c in gs.zones.hand:
            if c.name == BOLT:
                burn_damage += 3
            elif c.name == LAVA_DART:
                burn_damage += 1
        # Flashback dart
        if any(c.name == LAVA_DART for c in gs.zones.graveyard):
            burn_damage += 1

        total = base_power + prowess_damage + mutagenic_bonus + burn_damage
        return total

    # ------------------------------------------------------------------
    # Main phase — opponent-aware decisions
    # ------------------------------------------------------------------

    def _trigger_prowess(self, gs: GameState, spell_name: str = "spell"):
        """Give all prowess creatures +1/+1 until EOT."""
        for c in gs.zones.battlefield:
            if c.is_land():
                continue
            if c.name in PROWESS_CREATURES or ('Monk' in c.name and 'Token' in c.name):
                c.counters += 1
                self._prowess_boosts.append(c)

    def _try_plot_slickshot(self, gs: GameState) -> bool:
        """Plot Slickshot Show-Off if in hand and we have 2 mana."""
        for c in list(gs.zones.hand):
            if c.name == SLICKSHOT and gs.mana_pool.total() >= 2:
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                self._plotted_cards.append(c)
                gs._log(f"  [PLOT] Slickshot Show-Off (exiled, cast free later)")
                return True
        return False

    def _cast_from_plot(self, gs: GameState) -> bool:
        """Cast plotted cards for free (they have haste)."""
        cast_any = False
        for c in list(self._plotted_cards):
            self._plotted_cards.remove(c)
            gs.zones.battlefield.append(c)
            c.turn_entered = gs.turn
            c.summoning_sickness = False  # haste from plot
            self._spells_this_turn += 1
            # Creature spell — does NOT trigger prowess
            # But DOES count for Flurry (2nd spell → Monk token)
            self._check_flurry(gs)
            gs._log(f"  [FROM PLOT] {c.name} (free, haste)")
            cast_any = True
        return cast_any

    def _cast_cori_steel(self, gs: GameState) -> bool:
        """Cast Cori-Steel Cutter as equipment (artifact, triggers prowess)."""
        for c in list(gs.zones.hand):
            if c.name == CORI and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                self._cori_on_battlefield = True
                self._spells_this_turn += 1
                # Artifact = noncreature spell → triggers prowess
                self._trigger_prowess(gs, CORI)
                gs.noncreature_spells_this_turn += 1
                self._check_flurry(gs)
                gs._log(f"  Cast: Cori-Steel Cutter (equipment, prowess trigger)")
                return True
        return False

    def _check_flurry(self, gs: GameState):
        """Flurry: if this is the 2nd spell this turn, create a Monk token."""
        if self._spells_this_turn == 2 and self._cori_on_battlefield:
            token = gs._make_token("Monk Token", "1", "1", "Creature — Monk")
            token.summoning_sickness = False  # Cori gives haste
            # Cori auto-attaches: +1/+1, trample, haste
            token.counters += 1  # +1/+1 from equipment
            self._monks_created += 1
            gs._log(f"  [FLURRY] Cori-Steel → 1/1 Monk (now 2/2 haste trample prowess)")

    def main_phase(self, gs: GameState):
        """Goldfish fallback — just chain everything."""
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """
        Opponent-aware main phase.
        
        Core decision: is this THE TURN (burst kill)?
        If yes: deploy everything, chain all spells, go for lethal.
        If no: develop board, plot Slickshot, hold fuel for burst.
        """
        self._reset_turn()

        # Play a land
        self._play_land_if_able(gs)

        opp_life = opponent.life if opponent else 20
        burst = self._calc_burst_damage(gs)
        is_burst_turn = burst >= opp_life

        if is_burst_turn:
            self._execute_burst_turn(gs, opponent)
        else:
            self._execute_setup_turn(gs, opponent)

    def _execute_setup_turn(self, gs: GameState, opponent: GameState):
        """
        Not lethal yet — develop board and hold fuel.
        
        Priority:
        1. Deploy a threat if we have none
        2. Plot Slickshot for future burst turn
        3. Cast Cori-Steel (equipment, stays on board)
        4. Hold free spells (Bauble, Mutagenic) for burst turn
        5. Use removal on opponent's key threats
        """
        has_threat = any(c.name in PROWESS_CREATURES or c.name == DRC
                         for c in gs.zones.battlefield if not c.is_land())

        # 1. Deploy a threat if we have none
        if not has_threat:
            for name in (SWIFTSPEAR, DRC):
                for c in list(gs.zones.hand):
                    if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        gs.cast_spell(c)
                        self._spells_this_turn += 1
                        self._check_flurry(gs)
                        has_threat = True
                        break
                if has_threat:
                    break

        # 2. Plot Slickshot (invest 2 mana now for free haste creature later)
        if any(c.name == SLICKSHOT for c in gs.zones.hand):
            self._try_plot_slickshot(gs)

        # 3. Cast Cori-Steel Cutter (equipment, stays on board for flurry)
        if not self._cori_on_battlefield:
            self._cast_cori_steel(gs)

        # 4. Use removal on opponent's biggest threat (if worth it)
        if opponent:
            self._use_removal(gs, opponent)

        # 5. Attack with whatever we have (chip damage)
        # (handled by declare_attackers)

    def _use_removal(self, gs: GameState, opponent: GameState):
        """Use Bolt/Dart/Unholy Heat on opponent's best creature if worth it."""
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures:
            return

        best_target = max(opp_creatures, key=lambda c: safe_power(c))
        target_power = safe_power(best_target)

        # Only remove if the creature is a real threat
        if target_power < 2:
            return

        # Check removal spells in hand
        for c in list(gs.zones.hand):
            if c.name == UNHOLY and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                if best_target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(best_target)
                    opponent.zones.graveyard.append(best_target)
                self._trigger_prowess(gs, UNHOLY)
                self._spells_this_turn += 1
                self._check_flurry(gs)
                gs._log(f"  Unholy Heat → kill {best_target.name}")
                return

            if c.name == BOLT and target_power <= 3:
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    if safe_toughness(best_target) <= 3:
                        if best_target in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(best_target)
                            opponent.zones.graveyard.append(best_target)
                        gs._log(f"  Bolt → kill {best_target.name}")
                    else:
                        gs._log(f"  Bolt → {best_target.name} (survives)")
                    self._trigger_prowess(gs, BOLT)
                    self._spells_this_turn += 1
                    self._check_flurry(gs)
                    return

    def _execute_burst_turn(self, gs: GameState, opponent: GameState):
        """
        THE TURN — chain everything for lethal.
        
        Sequence matters:
        1. Deploy creatures first (Cori-Steel, then Slickshot from plot)
           — creature spells don't trigger prowess but count for Flurry
        2. Chain all noncreature spells (each triggers prowess on ALL creatures)
        3. Burn spells go face (not at creatures — we're going for the kill)
        4. Hold Mutagenic Growth for combat trick (after blockers)
        """
        # 1. Cast Cori-Steel Cutter (artifact = noncreature, triggers prowess + Flurry)
        if not self._cori_on_battlefield:
            self._cast_cori_steel(gs)

        # 2. Cast creatures from hand (no prowess triggers, but count for Flurry)
        for name in (SWIFTSPEAR, DRC):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    self._spells_this_turn += 1
                    self._check_flurry(gs)
                    break

        # 3. Cast Slickshot from plot (FREE, haste, creature — no prowess)
        self._cast_from_plot(gs)

        # 4. Chain free noncreature spells — each triggers prowess on ALL creatures
        # Baubles first (free, draw cards)
        for c in list(gs.zones.hand):
            if c.name == BAUBLE:
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                gs.zones.draw(1)
                self._trigger_prowess(gs, BAUBLE)
                self._spells_this_turn += 1
                gs.noncreature_spells_this_turn += 1
                self._check_flurry(gs)
                gs._log(f"  Bauble: draw 1 + prowess")

        # Lava Dart from hand
        for c in list(gs.zones.hand):
            if c.name == LAVA_DART:
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.damage_dealt += 1
                    self._trigger_prowess(gs, LAVA_DART)
                    self._spells_this_turn += 1
                    gs.noncreature_spells_this_turn += 1
                    self._check_flurry(gs)
                    gs._log(f"  Lava Dart face: 1 dmg ({gs.damage_dealt} total) + prowess")

        # Lava Dart flashback from GY
        dart_in_gy = next((c for c in gs.zones.graveyard if c.name == LAVA_DART), None)
        if dart_in_gy:
            mountains = [c for c in gs.zones.battlefield
                         if 'mountain' in (c.type_line or '').lower() and not c.tapped]
            if mountains:
                gs.zones.battlefield.remove(mountains[0])
                gs.zones.graveyard.append(mountains[0])
                gs.zones.graveyard.remove(dart_in_gy)
                gs.zones.exile.append(dart_in_gy)
                gs.damage_dealt += 1
                self._trigger_prowess(gs, "Lava Dart (flashback)")
                self._spells_this_turn += 1
                gs.noncreature_spells_this_turn += 1
                self._check_flurry(gs)
                gs._log(f"  Lava Dart flashback: 1 dmg ({gs.damage_dealt} total) + prowess")

        # Lightning Bolt face — big prowess trigger + 3 damage
        for c in list(gs.zones.hand):
            if c.name == BOLT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                gs.damage_dealt += 3
                self._trigger_prowess(gs, BOLT)
                self._spells_this_turn += 1
                gs.noncreature_spells_this_turn += 1
                self._check_flurry(gs)
                gs._log(f"  Bolt face: 3 dmg ({gs.damage_dealt} total) + prowess")

        # Cantrips for extra prowess triggers
        for c in list(gs.zones.hand):
            if c.name in (PREORDAIN, ITERATION):
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    gs.zones.draw(1)
                    self._trigger_prowess(gs, c.name)
                    self._spells_this_turn += 1
                    self._check_flurry(gs)

        # NOTE: Mutagenic Growth is held for combat_trick() after blockers

    # ------------------------------------------------------------------
    # Combat — attackers, blockers, combat tricks
    # ------------------------------------------------------------------

    def declare_attackers(self, gs: GameState, opponent: GameState) -> list:
        """Attack with everything that can attack."""
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land():
                continue
            if c.name == CORI:
                continue  # Cori-Steel is equipment, doesn't attack
            if getattr(c, 'summoning_sickness', False):
                continue
            if getattr(c, 'tapped', False):
                continue
            attackers.append(c)
        return attackers

    def declare_blockers(self, gs, opponent_gs, attackers):
        """Prowess deck rarely blocks — race or die."""
        return {}

    def combat_trick(self, gs: GameState, opponent: GameState,
                     attackers: list, blocker_assignments: dict) -> Optional[Card]:
        """
        Cast Mutagenic Growth AFTER blockers are declared.
        
        Target selection:
        - If Slickshot is unblocked (flying), pump Slickshot for max damage
        - Otherwise pump the biggest unblocked attacker
        - Each Mutagenic triggers prowess on ALL creatures (+1/+1 each)
          plus +2/+2 on the target
        """
        mutagenic = next((c for c in gs.zones.hand if c.name == MUTAGENIC), None)
        if not mutagenic:
            return None

        # Find best target: unblocked attacker with highest power
        blocked_creatures = set()
        for attacker, blockers in blocker_assignments.items():
            if blockers:
                blocked_creatures.add(id(attacker))

        unblocked = [a for a in attackers if id(a) not in blocked_creatures]
        if not unblocked:
            # All blocked — pump the one in the worst trade
            if attackers:
                target = max(attackers, key=lambda c: safe_power(c))
            else:
                return None
        else:
            # Pump unblocked creature (prefer Slickshot for flying damage)
            slickshot = next((c for c in unblocked if c.name == SLICKSHOT), None)
            if slickshot:
                target = slickshot
            else:
                target = max(unblocked, key=lambda c: safe_power(c))

        # Cast Mutagenic Growth (pay 2 life)
        gs.life -= 2
        gs.zones.hand.remove(mutagenic)
        gs.zones.graveyard.append(mutagenic)

        # +2/+2 on target
        target.counters += 2
        self._prowess_boosts.append(target)
        self._prowess_boosts.append(target)

        # Prowess trigger on ALL prowess creatures
        self._trigger_prowess(gs, MUTAGENIC)
        self._spells_this_turn += 1
        gs.noncreature_spells_this_turn += 1
        self._check_flurry(gs)

        gs._log(f"  [COMBAT TRICK] Mutagenic Growth on {target.name} "
                f"(+2/+2 pump + prowess on all, paid 2 life)")
        return mutagenic

    def respond_to_spell(self, gs, opponent, spell):
        """Prowess doesn't run reactive interaction — it's all-in aggro."""
        return None

    def end_step_actions(self, gs: GameState, opponent: GameState):
        """Clean up prowess boosts at end of turn."""
        for c in self._prowess_boosts:
            if c in gs.zones.battlefield:
                c.counters = max(0, c.counters - 1)
        self._prowess_boosts = []

    def _play_land_if_able(self, gs: GameState):
        """Play best land from hand."""
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        # Prefer fetches > shocks > basics
        def score(c):
            n = c.name.lower()
            if 'mesa' in n or 'tarn' in n or 'delta' in n or 'mire' in n:
                return 0
            if 'vents' in n or 'foundry' in n:
                return 1
            if 'islet' in n or 'fiery' in n:
                return 2
            return 3
        best = min(lands, key=score)
        gs.play_land(best)
