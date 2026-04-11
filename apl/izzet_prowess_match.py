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

# Creatures with prowess (+1/+1 on noncreature cast)
PROWESS_CREATURES = {SWIFTSPEAR, DRC}
# Note: Monk tokens from Cori-Steel also have prowess (+1/+1)
# Slickshot has a CUSTOM ability: +2/+0 per noncreature (NOT prowess)
SLICKSHOT_BOOST = 2  # +2/+0, not +1/+1

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

    def _has_delirium(self, gs: GameState) -> bool:
        """Check if 4+ card types in GY (for DRC + Unholy Heat)."""
        types_in_gy = set()
        for c in gs.zones.graveyard:
            tl = (getattr(c, 'type_line', '') or '').lower()
            for t in ('creature', 'instant', 'sorcery', 'artifact', 'enchantment', 'land'):
                if t in tl:
                    types_in_gy.add(t)
        return len(types_in_gy) >= 4

    def _drc_power(self, gs: GameState) -> int:
        """DRC base power: 1 normally, 3 with delirium (3/3 flyer)."""
        return 3 if self._has_delirium(gs) else 1

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
        """Count creatures with standard prowess (+1/+1) on the battlefield.
        Does NOT count Slickshot (which has +2/+0 custom ability)."""
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
        # Violent Urge cantrips (draws a card — likely another spell)
        # Oracle: "Target creature gets +1/+0 and gains first strike. Draw a card."
        violent_count = sum(1 for c in gs.zones.hand if c.name == VIOLENT)
        count += violent_count  # each Violent Urge = 2 prowess triggers (itself + drawn card)
        return count

    def _calc_burst_damage(self, gs: GameState) -> int:
        """
        Calculate maximum damage if we chain all spells this turn.
        This is the combo kill calculation.
        """
        prowess_creatures = self._count_prowess_on_board(gs)
        fuel = self._count_noncreature_fuel(gs)

        # Base power of each attacking creature
        # DRC: 3/3 with delirium, 1/1 without
        delirium = self._has_delirium(gs)
        base_power = 0
        for c in gs.zones.battlefield:
            if c.is_land():
                continue
            if getattr(c, 'summoning_sickness', False):
                continue
            if c.name == DRC:
                base_power += 3 if delirium else 1
            else:
                base_power += safe_power(c)

        # Plotted Slickshot adds 1 base power (1/2 stats) with haste
        plotted_slickshots = sum(1 for c in self._plotted_cards if c.name == SLICKSHOT)
        if plotted_slickshots:
            base_power += 1 * plotted_slickshots  # 1/2 base stats

        # Each noncreature spell gives:
        #   +1 power to each standard prowess creature (Swiftspear, DRC, Monks)
        #   +2 power to each Slickshot Show-Off
        prowess_damage = fuel * prowess_creatures  # standard prowess
        
        # Count Slickshots on board + plotted
        slickshots_on_board = sum(1 for c in gs.zones.battlefield
                                  if c.name == SLICKSHOT
                                  and not getattr(c, 'summoning_sickness', False))
        total_slickshots = slickshots_on_board + plotted_slickshots
        slickshot_damage = fuel * total_slickshots * SLICKSHOT_BOOST  # +2/+0 each

        # Mutagenic Growth gives +2/+2 to one creature ON TOP of prowess
        has_mutagenic = any(c.name == MUTAGENIC for c in gs.zones.hand)
        mutagenic_bonus = 2 if has_mutagenic else 0

        # Violent Urge: +1/+0 + first strike + draw. With delirium: DOUBLE STRIKE
        # Double strike DOUBLES the combat damage of the target creature
        has_violent = any(c.name == VIOLENT for c in gs.zones.hand)
        violent_double_strike = delirium and has_violent

        # Cori-Steel Flurry: if Cori on board and we cast 2+ spells, adds a 2/2 haste Monk
        cori_on_board = any(c.name == CORI for c in gs.zones.battlefield) or self._cori_on_battlefield
        monk_damage = 0
        if cori_on_board and fuel >= 2:
            # Monk starts as 2/2 (1/1 + equipment +1/+1), has prowess
            # Remaining spells after the 2nd one pump the Monk
            monk_prowess_triggers = max(0, fuel - 2)  # spells after Flurry trigger
            monk_damage = 2 + monk_prowess_triggers  # 2 base + prowess

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

        # Combat damage total
        combat_power = base_power + prowess_damage + slickshot_damage + mutagenic_bonus + monk_damage
        
        # If Violent Urge gives double strike (delirium), double the BEST creature's combat
        # Apply double strike to Slickshot (highest damage output with +2/+0 per spell)
        if violent_double_strike and total_slickshots > 0:
            # Slickshot's contribution gets doubled
            slickshot_power = 1 + (fuel * SLICKSHOT_BOOST) + (mutagenic_bonus if total_slickshots else 0) + 1  # +1 from Violent Urge
            combat_power += slickshot_power  # add it again = double strike
        elif violent_double_strike and prowess_creatures > 0:
            # Double strike on best prowess creature
            best_prowess = max(1, base_power // max(prowess_creatures, 1)) + fuel
            combat_power += best_prowess
        
        total = combat_power + burn_damage
        return total

    # ------------------------------------------------------------------
    # Main phase — opponent-aware decisions
    # ------------------------------------------------------------------

    def _trigger_prowess(self, gs: GameState, spell_name: str = "spell"):
        """Give prowess creatures +1/+1 and Slickshot +2/+0 until EOT."""
        for c in gs.zones.battlefield:
            if c.is_land():
                continue
            if c.name in PROWESS_CREATURES or ('Monk' in c.name and 'Token' in c.name):
                # Standard prowess: +1/+1
                c.counters += 1
                self._prowess_boosts.append(c)
            elif c.name == SLICKSHOT:
                # Slickshot's custom ability: +2/+0 (power only)
                c.counters += SLICKSHOT_BOOST
                self._prowess_boosts.append(c)
                self._prowess_boosts.append(c)  # track 2 counters to remove

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
        
        # Against lifegain decks, pad SLIGHTLY for expected lifegain
        # Don't over-pad — better to burst for near-lethal than wait forever
        if opponent:
            lifegain_sources = sum(1 for c in opponent.zones.battlefield
                                   if c.name in ("Guide of Souls", "Ocelot Pride",
                                                  "Phlage, Titan of Fire's Fury"))
            opp_life += min(lifegain_sources * 2, 4)  # cap at +4 padding
        
        burst = self._calc_burst_damage(gs)
        is_burst_turn = burst >= opp_life
        
        # DESPERATION: if T5+ and we haven't burst, go all-in
        # Waiting only helps lifegain compound — commit everything
        if not is_burst_turn and gs.turn >= 5:
            burst_pct = burst / max(1, opp_life)
            if burst_pct >= 0.7:  # can deal 70%+ of their life
                is_burst_turn = True  # go for it, hope they don't have the answer

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
        5. Use removal on opponent's key threats ONLY if they threaten lethal
        
        PLAY AROUND REMOVAL:
        - Don't deploy a 2nd creature if opponent has 1+ mana open and
          removal in their colors (we already have a threat)
        - Better to hold creatures and deploy on burst turn when we
          can protect with combat tricks
        """
        has_threat = any(c.name in PROWESS_CREATURES or c.name == DRC
                         for c in gs.zones.battlefield if not c.is_land())

        # Check if opponent has removal mana open
        opp_mana_open = 0
        if opponent:
            opp_mana_open = opponent.mana_pool.total() if hasattr(opponent.mana_pool, 'total') else 0

        # 1. Deploy a threat if we have NONE (must develop)
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
        #    SAFE: plotting doesn't put creature on battlefield, can't be removed
        if any(c.name == SLICKSHOT for c in gs.zones.hand):
            self._try_plot_slickshot(gs)

        # 3. Cast Cori-Steel Cutter (equipment — safe, can't be Bolted)
        if not self._cori_on_battlefield:
            self._cast_cori_steel(gs)

        # 4. Deploy additional creatures — Prowess WANTS threats on board
        #    Even if they might get Bolted, you need creatures to carry prowess triggers
        #    The key is holding SPELLS for burst, not holding CREATURES
        for name in (SWIFTSPEAR, DRC):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    self._spells_this_turn += 1
                    self._check_flurry(gs)
                    break

        # 5. Use removal ONLY on high-value targets
        if opponent:
            self._use_removal_sparingly(gs, opponent)

        # 6. Cast ONE Bauble per setup turn for chip prowess + draw
        #    Don't hold ALL fuel — use free spells to pump chip damage
        for c in list(gs.zones.hand):
            if c.name == BAUBLE:
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                gs.zones.draw(1)
                self._trigger_prowess(gs, BAUBLE)
                self._spells_this_turn += 1
                gs.noncreature_spells_this_turn += 1
                self._check_flurry(gs)
                break  # only one per setup turn

        # 7. Cast one cantrip for prowess + dig toward burst pieces
        for c in list(gs.zones.hand):
            if c.name in (PREORDAIN, ITERATION):
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    gs.zones.draw(1)
                    self._trigger_prowess(gs, c.name)
                    self._spells_this_turn += 1
                    self._check_flurry(gs)
                    break

    def _use_removal_sparingly(self, gs: GameState, opponent: GameState):
        """Remove Boros engine pieces FIRST, then big threats. Save Bolt for burst face.
        
        From competitive guides: "Focus on individual threats, making it difficult for 
        opponent to establish Guide of Souls + Ocelot Pride, or Ajani + Bombardment."
        
        Priority kill targets (vs Boros):
        1. Guide of Souls (1/2) — THE engine piece. Kill with Lava Dart or Unholy Heat.
        2. Ocelot Pride (1/1) — token generator. Kill with Lava Dart.
        3. Cori-Steel Cutter (on our side - opponent perspective: kill our Cutter too)
        4. Phlage (gains 3 life per attack)
        5. Screaming Nemesis (3/3, reflects damage — use exile not burn)
        6. Any creature with 4+ power (racing threat)
        
        Save Lightning Bolt for FACE damage on burst turn when possible.
        Use Lava Dart and Unholy Heat for creature removal (lower opportunity cost).
        """
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures:
            return

        # Priority: Engine pieces > Big threats > Everything else
        engine_pieces = [c for c in opp_creatures
                         if c.name in ("Guide of Souls", "Ocelot Pride", "Ajani, Nacatl Pariah")]
        big_threats = [c for c in opp_creatures
                       if safe_power(c) >= 4
                       or c.name == "Phlage, Titan of Fire's Fury"
                       or c.name == "Screaming Nemesis"]
        
        must_kill = engine_pieces if engine_pieces else big_threats
        if not must_kill:
            return

        target = max(must_kill, key=lambda c: safe_power(c))
        target_t = safe_toughness(target)
        
        # Use Lava Dart on 1-toughness engine pieces (Guide, Ocelot, Ragavan)
        if target_t <= 1:
            for c in list(gs.zones.hand):
                if c.name == LAVA_DART and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    if target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.graveyard.append(target)
                    self._trigger_prowess(gs, LAVA_DART)
                    self._spells_this_turn += 1
                    self._check_flurry(gs)
                    gs._log(f"  Lava Dart → kill {target.name} (engine piece)")
                    return

        # Use Unholy Heat first (preserves Bolt for face on burst turn)
        # Oracle: 2 damage, or 6 with delirium (4+ card types in GY)
        delirium = self._has_delirium(gs)
        unholy_dmg = 6 if delirium else 2
        for c in list(gs.zones.hand):
            if c.name == UNHOLY and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                if unholy_dmg < target_t:
                    continue  # won't kill without delirium
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                if target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.graveyard.append(target)
                self._trigger_prowess(gs, UNHOLY)
                self._spells_this_turn += 1
                self._check_flurry(gs)
                gs._log(f"  Unholy Heat ({unholy_dmg} dmg, {'delirium' if delirium else 'no delirium'}) → kill {target.name}")
                return

        # Only use Bolt on 4+ power threats — save it for face otherwise
        if safe_power(target) >= 4 and target_t <= 3:
            for c in list(gs.zones.hand):
                if c.name == BOLT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    if target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.graveyard.append(target)
                    self._trigger_prowess(gs, BOLT)
                    self._spells_this_turn += 1
                    self._check_flurry(gs)
                    gs._log(f"  Bolt → kill {target.name} (must-kill, 4+ power)")
                    return

    def _use_removal(self, gs: GameState, opponent: GameState):
        """Legacy method — redirects to sparingly."""
        self._use_removal_sparingly(gs, opponent)

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
        # Baubles first (free, draw cards) — cast ALL of them
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

        # Lava Dart from hand — cast ALL
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

        # Lightning Bolt face — ALL of them, big prowess triggers + damage
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
        violent = next((c for c in gs.zones.hand if c.name == VIOLENT), None)
        if not mutagenic and not violent:
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

        # Cast Mutagenic Growth (pay 2 life) if available
        if mutagenic:
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

        # Also cast Violent Urge if in hand — +1/+0, first strike, draw a card
        # With delirium: DOUBLE STRIKE (devastating on Slickshot)
        violent = next((c for c in gs.zones.hand if c.name == VIOLENT), None)
        if violent and gs.mana_pool.can_cast(violent.mana_cost, violent.cmc):
            gs.mana_pool.pay(violent.mana_cost, violent.cmc)
            gs.zones.hand.remove(violent)
            gs.zones.graveyard.append(violent)
            target.counters += 1  # +1/+0
            self._trigger_prowess(gs, VIOLENT)
            self._spells_this_turn += 1
            gs.noncreature_spells_this_turn += 1
            self._check_flurry(gs)
            # Draw a card (cantrip)
            gs.zones.draw(1)
            delirium = self._has_delirium(gs)
            mode = "DOUBLE STRIKE" if delirium else "first strike"
            gs._log(f"  [COMBAT TRICK] Violent Urge on {target.name} "
                    f"(+1/+0, {mode}, draw 1 + prowess)")

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
