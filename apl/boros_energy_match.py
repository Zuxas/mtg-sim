"""
apl/boros_energy_match.py — Match-aware Boros Energy APL (Modern)

Key differences from goldfish APL:
1. Bolt/Galvanic/Phlage target opponent CREATURES (not face)
2. Static Prison is LIVE (exile their best creature + 2 energy)
3. Thraben Charm kills creatures (2× creature count damage)
4. Prioritize lifegain engine (Guide → Ocelot → Ajani tokens)
5. Block with expendable tokens
6. Galvanic Discharge spends energy on opponent creatures (not self-target)
7. Bombardment sacrifices creatures in response to removal, not just for lethal

The Boros heuristic vs Prowess:
"Every 3 life gained costs them 1 card from hand. Don't race — just survive
and let the value engine compound. Kill their threats on sight."
"""

from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness, has_keyword
from engine.stack import classify_card, InteractionType, get_burn_damage

# Card names
RAGAVAN          = "Ragavan, Nimble Pilferer"
OCELOT_PRIDE     = "Ocelot Pride"
AJANI            = "Ajani, Nacatl Pariah"
GUIDE_OF_SOULS   = "Guide of Souls"
GOBLIN_BOMBARD   = "Goblin Bombardment"
SEASONED_PYRO    = "Seasoned Pyromancer"
PHLAGE           = "Phlage, Titan of Fire's Fury"
SCREAMING_NEMESIS = "Screaming Nemesis"
GALVANIC         = "Galvanic Discharge"
STATIC_PRISON    = "Static Prison"
THRABEN_CHARM    = "Thraben Charm"
LIGHTNING_BOLT   = "Lightning Bolt"
VOICE_OF_VICTORY = "Voice of Victory"

# Dead in goldfish but LIVE in match mode
REMOVAL_SPELLS = {LIGHTNING_BOLT, GALVANIC, STATIC_PRISON, THRABEN_CHARM}


class BorosEnergyMatchAPL(MatchAPL):
    name = "Boros Energy"
    win_condition_damage = 20
    max_turns = 12

    def __init__(self):
        self._treasures = 0
        self._gained_life_this_turn = False
        self._tokens_entered = 0
        self._mobilize_tokens = 0  # Voice of Victory Warrior tokens to sacrifice
        self._ajani_pw_active = False  # Ajani transformed into planeswalker
        self._ajani_pw_loyalty = 0

    def _grant_arena_haste(self, gs, creature):
        """Arena of Glory: if untapped Arena on board, creature gets haste.
        Oracle: "{R}, {T}, Exert: Add {R}{R}. If mana spent on creature spell, it gains haste."
        Works on: Voice of Victory, Seasoned Pyromancer, Clarion Conqueror, Ajani, etc.
        """
        arena = next((c for c in gs.zones.battlefield
                      if 'arena of glory' in (c.name or '').lower()
                      and not getattr(c, 'tapped', False)), None)
        if arena and getattr(creature, 'summoning_sickness', False):
            creature.summoning_sickness = False
            gs._log(f"  Arena of Glory haste: {creature.name}")

    # ------------------------------------------------------------------
    # Mulligan
    # ------------------------------------------------------------------

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        creatures = sum(1 for c in hand if c.has(Tag.CREATURE))
        ones = sum(1 for c in hand if c.has(Tag.ONE_DROP) and not c.is_land())
        removal = sum(1 for c in hand if c.name in REMOVAL_SPELLS)
        if lands == 0:
            return False
        if lands > 4:
            return False
        # In match mode, hands with removal + threats are premium
        if lands >= 2 and creatures >= 1 and removal >= 1:
            return True
        if lands >= 2 and ones >= 1:
            return True
        if any(c.name == RAGAVAN for c in hand) and lands >= 1:
            return True
        if lands >= 2 and creatures >= 2:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        to_bottom = []
        if len(lands) > 3:
            to_bottom.extend(lands[3:])
        for c in spells:
            if len(to_bottom) >= n:
                break
            if c.cmc >= 3 and c not in to_bottom:
                to_bottom.append(c)
        for c in spells:
            if len(to_bottom) >= n:
                break
            if c not in to_bottom:
                to_bottom.append(c)
        return to_bottom[:n]

    # ------------------------------------------------------------------
    # Removal targeting — kill their best creature
    # ------------------------------------------------------------------

    def _use_removal_on_creatures(self, gs: GameState, opponent: GameState):
        """
        Use removal on opponent's creatures. Priority:
        1. Bolt kills anything with toughness ≤3
        2. Static Prison exiles anything (gives us 2 energy)
        3. Galvanic Discharge — spend energy to kill a creature
        4. Thraben Charm — deals 2× our creature count to a target creature
        """
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures:
            return

        # Sort by threat level — highest power first
        opp_creatures.sort(key=lambda c: -safe_power(c))
        best_target = opp_creatures[0]
        target_toughness = safe_toughness(best_target)

        # 1. Lightning Bolt — kills ≤3 toughness
        if target_toughness <= 3:
            for c in list(gs.zones.hand):
                if c.name == LIGHTNING_BOLT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.noncreature_spells_this_turn += 1
                    if best_target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(best_target)
                        opponent.zones.graveyard.append(best_target)
                    gs._log(f"  Bolt → kill {best_target.name} (T≤3)")
                    return

        # 2. Static Prison — exile anything, gain 2 energy
        for c in list(gs.zones.hand):
            if c.name == STATIC_PRISON and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.battlefield.append(c)  # enchantment stays on board
                c.turn_entered = gs.turn
                gs.energy = getattr(gs, 'energy', 0) + 2
                gs.noncreature_spells_this_turn += 1
                if best_target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(best_target)
                    opponent.zones.exile.append(best_target)
                gs._log(f"  Static Prison → exile {best_target.name} (+2 energy)")
                return

        # 3. Galvanic Discharge — spend accumulated energy
        energy = getattr(gs, 'energy', 0)
        if energy >= target_toughness:
            for c in list(gs.zones.hand):
                if c.name == GALVANIC and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.energy = getattr(gs, 'energy', 0) + 3  # ETB gives 3 energy
                    spent = min(gs.energy, target_toughness)
                    gs.energy -= spent
                    gs.noncreature_spells_this_turn += 1
                    if spent >= target_toughness and best_target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(best_target)
                        opponent.zones.graveyard.append(best_target)
                        gs._log(f"  Galvanic → {spent} dmg, kill {best_target.name} (energy left: {gs.energy})")
                    else:
                        gs._log(f"  Galvanic → {spent} dmg to {best_target.name} (survives)")
                    return

        # 4. Thraben Charm — 2× creature count damage to target creature
        our_creatures = sum(1 for c in gs.zones.battlefield
                            if not c.is_land() and c.has(Tag.CREATURE))
        charm_damage = our_creatures * 2
        if charm_damage >= target_toughness:
            for c in list(gs.zones.hand):
                if c.name == THRABEN_CHARM and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.noncreature_spells_this_turn += 1
                    if best_target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(best_target)
                        opponent.zones.graveyard.append(best_target)
                    gs._log(f"  Thraben Charm → {charm_damage} dmg, kill {best_target.name}")
                    return

    # ------------------------------------------------------------------
    # Main phase — prioritize lifegain engine + removal
    # ------------------------------------------------------------------

    def main_phase(self, gs: GameState):
        """Goldfish fallback."""
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """
        Match-aware main phase.
        
        Priority order:
        1. Play land
        2. Kill opponent's best creature with removal
        3. Deploy lifegain engine: Guide of Souls → Ocelot Pride → Ajani
        4. Haste creatures (Ragavan, Screaming Nemesis) pre-combat
        5. Goblin Bombardment (sac outlet)
        6. Galvanic for energy (self-target if no opponent creatures)
        """
        self._gained_life_this_turn = False
        self._tokens_entered = 0

        # Treasure mana
        if self._treasures > 0:
            use = min(self._treasures, 3)
            gs.mana_pool.flex += use
            self._treasures -= use

        # 1. Play land
        self._play_land_if_able(gs)

        # 1a. STATIC PRISON MAINTENANCE — pay {E} per prison or lose it
        # Oracle: "At the beginning of your first main phase, sacrifice unless you pay {E}"
        prisons = [c for c in gs.zones.battlefield if c.name == STATIC_PRISON]
        energy = getattr(gs, 'energy', 0)
        for prison in prisons:
            if energy >= 1:
                energy -= 1
                gs.energy = energy
            else:
                # Can't pay — prison breaks, exiled card returns
                gs.zones.battlefield.remove(prison)
                gs.zones.graveyard.append(prison)
                gs._log(f"  Static Prison falls off (no energy to maintain)")

        # 1b. AJANI PLANESWALKER — 0 ability: create Cat + deal damage = creature count
        # Oracle (back face): "0: Create a 2/1 Cat Warrior token. When you do, if you
        #   control another red permanent, deals damage = number of creatures to any target."
        # Balanced by: opponent can attack PW or Bolt it. Subtract opponent pressure each turn.
        if self._ajani_pw_active and self._ajani_pw_loyalty > 0:
            # Count creatures and red permanents
            creatures = [c for c in gs.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
            has_red = any('mountain' in (getattr(c, 'type_line', '') or '').lower() or
                         c.name in (GOBLIN_BOMBARD, RAGAVAN, SCREAMING_NEMESIS, SEASONED_PYRO)
                         for c in gs.zones.battlefield)
            
            # 0 ability: create Cat + damage
            token = gs._make_token("Cat Warrior Token", "2", "1", "Creature — Cat Warrior")
            self._tokens_entered += 1
            guides = sum(1 for c in gs.zones.battlefield if c.name == GUIDE_OF_SOULS)
            if guides:
                gs.life += guides
                gs.energy = getattr(gs, 'energy', 0) + guides
                self._gained_life_this_turn = True
            
            creature_count = len(creatures) + 1  # +1 for the new token
            if has_red:
                gs.damage_dealt += creature_count
                gs._log(f"  Ajani PW 0: Cat token + {creature_count} dmg to face (Loyalty {self._ajani_pw_loyalty})")
            
            # Opponent pressure: simulate that opponent can attack/Bolt the PW
            # ~2 effective damage per turn from opponent interaction
            if opponent:
                opp_power = sum(safe_power(c) for c in opponent.zones.battlefield
                                if not c.is_land() and c.has(Tag.CREATURE)
                                and not getattr(c, 'summoning_sickness', False))
                pw_damage = min(opp_power, 3)  # cap at 3 per turn (one attacker redirected)
                self._ajani_pw_loyalty -= pw_damage
                if self._ajani_pw_loyalty <= 0:
                    self._ajani_pw_active = False
                    gs._log(f"  Ajani PW dies to opponent pressure")

        # 2. REMOVAL FIRST — kill their threats before they combo
        if opponent:
            self._use_removal_on_creatures(gs, opponent)

        # 3. Deploy lifegain engine creatures (priority order)
        # Guide of Souls is #1 — every creature entering = +1 life +1 energy
        for name in (GUIDE_OF_SOULS, OCELOT_PRIDE, AJANI, VOICE_OF_VICTORY):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    self._grant_arena_haste(gs, c)
                    # Guide triggers for itself entering
                    guides = sum(1 for x in gs.zones.battlefield if x.name == GUIDE_OF_SOULS)
                    if guides and c.has(Tag.CREATURE):
                        gs.life += guides
                        gs.energy = getattr(gs, 'energy', 0) + guides
                        self._gained_life_this_turn = True
                    # Ajani ETB: create 2/1 Cat token
                    if name == AJANI:
                        token = gs._make_token("Cat Warrior Token", "2", "1",
                                               "Creature — Cat Warrior")
                        self._tokens_entered += 1
                        if guides:
                            gs.life += guides
                            gs.energy = getattr(gs, 'energy', 0) + guides
                            self._gained_life_this_turn = True
                    break

        # 4. Haste creatures pre-combat
        from engine.keywords import KWTag
        for name in (RAGAVAN, SCREAMING_NEMESIS):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    self._grant_arena_haste(gs, c)
                    guides = sum(1 for x in gs.zones.battlefield if x.name == GUIDE_OF_SOULS)
                    if guides:
                        gs.life += guides
                        gs.energy = getattr(gs, 'energy', 0) + guides
                        self._gained_life_this_turn = True
                    break

        # 5. Goblin Bombardment
        for c in list(gs.zones.hand):
            if c.name == GOBLIN_BOMBARD and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 5a. Seasoned Pyromancer — discard 2, draw 2, create Elemental tokens
        # Oracle: "When enters, discard two cards, draw two cards. For each nonland
        #          card discarded this way, create a 1/1 red Elemental creature token."
        # Key synergy: discarding Phlage sets up GY for escape
        for c in list(gs.zones.hand):
            if c.name == SEASONED_PYRO and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                self._grant_arena_haste(gs, c)
                guides = sum(1 for x in gs.zones.battlefield if x.name == GUIDE_OF_SOULS)
                if guides:
                    gs.life += guides
                    gs.energy = getattr(gs, 'energy', 0) + guides
                    self._gained_life_this_turn = True
                # Discard 2: prefer Phlage (GY setup) > excess lands > highest CMC
                discarded_nonlands = 0
                for _ in range(2):
                    if not gs.zones.hand: break
                    # Priority: Phlage (want in GY for escape)
                    phlages = [x for x in gs.zones.hand if x.name == PHLAGE]
                    lands = [x for x in gs.zones.hand if x.is_land()]
                    if phlages:
                        d = phlages[0]; gs.zones.hand.remove(d); gs.zones.graveyard.append(d)
                        discarded_nonlands += 1
                    elif lands and len(lands) > 2:
                        d = lands[-1]; gs.zones.hand.remove(d); gs.zones.graveyard.append(d)
                    elif gs.zones.hand:
                        d = max(gs.zones.hand, key=lambda x: getattr(x, 'cmc', 0))
                        gs.zones.hand.remove(d); gs.zones.graveyard.append(d)
                        if not d.is_land(): discarded_nonlands += 1
                # Draw 2
                gs.zones.draw(2)
                # Create Elemental tokens for each nonland discarded
                for _ in range(discarded_nonlands):
                    gs._make_token("Elemental Token", "1", "1", "Creature - Elemental")
                    self._tokens_entered += 1
                    if guides:
                        gs.life += guides
                        gs.energy = getattr(gs, 'energy', 0) + guides
                        self._gained_life_this_turn = True
                gs._log(f"  Pyromancer: discard 2 (Phlage→GY), draw 2, +{discarded_nonlands} Elementals")
                break

        # 5b. PHLAGE — hardcast as removal, escape as finisher
        # Hardcast {1}{R}{W}: ETB 3 damage + 3 life, then SACRIFICE (not a creature!)
        # Escape {R}{R}{W}{W} + exile 5: STAYS as 6/6 haste
        guides = sum(1 for x in gs.zones.battlefield if x.name == GUIDE_OF_SOULS)
        
        # First: try to ESCAPE Phlage from GY (permanent 6/6)
        gy_phlages = [c for c in gs.zones.graveyard if c.name == PHLAGE]
        other_gy = len(gs.zones.graveyard) - len(gy_phlages)
        if gy_phlages and other_gy >= 5 and gs.mana_pool.total() >= 4:
            # Escape cost: {R}{R}{W}{W} (4 colored mana)
            if gs.mana_pool.can_pay("{R}{R}{W}{W}", 4):
                phlage = gy_phlages[0]
                gs.mana_pool.pay("{R}{R}{W}{W}", 4)
                gs.zones.graveyard.remove(phlage)
                # Exile 5 other cards from GY
                exiled = 0
                for x in list(gs.zones.graveyard):
                    if exiled >= 5: break
                    gs.zones.graveyard.remove(x)
                    gs.zones.exile.append(x)
                    exiled += 1
                gs.zones.battlefield.append(phlage)
                phlage.turn_entered = gs.turn
                # Arena of Glory: "If mana spent on creature spell, it gains haste"
                # Escaped Phlage can have haste if Arena provided mana
                has_arena = any('arena of glory' in (getattr(c, 'name', '') or '').lower()
                                for c in gs.zones.battlefield)
                phlage.summoning_sickness = not has_arena  # haste if Arena available
                # ETB: 3 damage + 3 life
                if opponent:
                    opp_creatures = [c for c in opponent.zones.battlefield
                                     if not c.is_land() and c.has(Tag.CREATURE)]
                    if opp_creatures:
                        target = max(opp_creatures, key=lambda c: safe_power(c))
                        if safe_toughness(target) <= 3 and target in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(target)
                            opponent.zones.graveyard.append(target)
                            gs._log(f"  PHLAGE ESCAPE → kill {target.name} + 3 life (6/6 STAYS)")
                        else:
                            gs.damage_dealt += 3
                            gs._log(f"  PHLAGE ESCAPE → 3 face + 3 life (6/6 STAYS)")
                    else:
                        gs.damage_dealt += 3
                        gs._log(f"  PHLAGE ESCAPE → 3 face + 3 life (6/6 STAYS)")
                gs.life += 3
                if guides: gs.life += guides; gs.energy = getattr(gs, 'energy', 0) + guides
        
        # Second: hardcast Phlage from hand as REMOVAL (sacrificed immediately)
        for c in list(gs.zones.hand):
            if c.name == PHLAGE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                # ETB: 3 damage + 3 life
                if opponent:
                    opp_creatures = [c2 for c2 in opponent.zones.battlefield
                                     if not c2.is_land() and c2.has(Tag.CREATURE)]
                    if opp_creatures:
                        target = max(opp_creatures, key=lambda c2: safe_power(c2))
                        if safe_toughness(target) <= 3 and target in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(target)
                            opponent.zones.graveyard.append(target)
                            gs._log(f"  Phlage hardcast → kill {target.name} + 3 life (then sacrifice)")
                        else:
                            gs.damage_dealt += 3
                            gs._log(f"  Phlage hardcast → 3 face + 3 life (then sacrifice)")
                    else:
                        gs.damage_dealt += 3
                gs.life += 3
                # SACRIFICE — goes to GY (available for escape later)
                gs.zones.graveyard.append(c)
                gs._log(f"  Phlage sacrificed (now in GY for future escape)")
                break

        # 6. Galvanic for energy if no opponent targets
        if not opponent or not any(not c.is_land() for c in opponent.zones.battlefield):
            for c in list(gs.zones.hand):
                if c.name == GALVANIC and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    creatures = gs.zones.creatures_on_battlefield()
                    if creatures:
                        gs.energy = getattr(gs, 'energy', 0) + 3
                        gs.cast_spell(c)
                        gs._log(f"  Galvanic: +3 energy (self-target, no opponent creatures)")
                    break

        # 7. Fill remaining mana with creatures (NOT Phlage — handled above)
        while True:
            castable = [c for c in gs.zones.hand
                        if c.has(Tag.CREATURE)
                        and c.name not in REMOVAL_SPELLS
                        and c.name != PHLAGE  # Phlage handled in step 5b
                        and gs.mana_pool.can_cast(c.mana_cost, c.cmc)]
            if not castable:
                break
            card = min(castable, key=lambda c: (c.cmc, c.name))
            if not gs.cast_spell(card):
                break
            self._grant_arena_haste(gs, card)
            guides = sum(1 for x in gs.zones.battlefield if x.name == GUIDE_OF_SOULS)
            if guides:
                gs.life += guides
                gs.energy = getattr(gs, 'energy', 0) + guides
                self._gained_life_this_turn = True

        # 8. NOTE: Ocelot tokens happen at END STEP (in end_step_actions), not here

    def _simulate_end_step(self, gs: GameState):
        """Ocelot Pride: create Cat token if we gained life this turn."""
        ocelots = sum(1 for c in gs.zones.battlefield if c.name == OCELOT_PRIDE)
        if ocelots > 0 and self._gained_life_this_turn:
            for _ in range(ocelots):
                token = gs._make_token("Cat Token", "1", "1", "Creature — Cat")
                self._tokens_entered += 1
                guides = sum(1 for c in gs.zones.battlefield if c.name == GUIDE_OF_SOULS)
                if guides:
                    gs.life += guides
                    gs.energy = getattr(gs, 'energy', 0) + guides
            gs._log(f"  Ocelot: {ocelots} Cat token(s)")

    # ------------------------------------------------------------------
    # Combat
    # ------------------------------------------------------------------

    def declare_attackers(self, gs: GameState, opponent: GameState) -> list:
        """Attack with non-essential creatures. Hold back key engine pieces
        if opponent has removal mana open.
        Also: Voice of Victory Mobilize 2 — creates 2 attacking 1/1 tokens per Voice attacking.
        """
        from engine.keywords import KWTag
        attackers = []
        voices_attacking = 0
        for c in gs.zones.battlefield:
            if c.is_land() or c.name == GOBLIN_BOMBARD:
                continue
            if getattr(c, 'summoning_sickness', False):
                continue
            if getattr(c, 'tapped', False):
                continue
            attackers.append(c)
            if c.name == VOICE_OF_VICTORY:
                voices_attacking += 1
        
        # Voice of Victory Mobilize 2: create 2x 1/1 Warriors per Voice attacking
        # Oracle: "create two tapped and attacking 1/1 red Warrior creature tokens.
        #          Sacrifice them at the beginning of the next end step."
        # Tokens enter tapped and attacking → trigger Guide of Souls
        # Tokens will be sacrificed at end step → sacrifice to Bombardment FIRST
        if voices_attacking > 0:
            new_tokens = voices_attacking * 2
            guides = sum(1 for c in gs.zones.battlefield if c.name == GUIDE_OF_SOULS)
            
            # Each token entering triggers Guide (gain life + energy)
            life_gained = new_tokens * guides
            gs.life += life_gained
            gs.energy = getattr(gs, 'energy', 0) + new_tokens * guides
            if life_gained > 0:
                self._gained_life_this_turn = True
            
            # Track tokens for Bombardment sacrifice at end step
            # DON'T add damage_dealt here — tokens go through combat normally
            self._tokens_entered += new_tokens
            self._mobilize_tokens = new_tokens  # track for end_step sacrifice
            gs._log(f"  Voice Mobilize: {voices_attacking} Voices → {new_tokens} Warrior tokens (+{life_gained} life)")
        
        # Guide of Souls attack pump: pay {E}{E}{E} → +2/+2 and flying on attacker
        # Oracle: "Whenever you attack, you may pay {E}{E}{E}. When you do, put two
        #          +1/+1 counters and a flying counter on target attacking creature."
        # Priority: Ragavan (4/3 flying + Treasure/exile) > others
        guides_on_board = sum(1 for c in gs.zones.battlefield if c.name == GUIDE_OF_SOULS)
        if guides_on_board > 0 and attackers:
            energy = getattr(gs, 'energy', 0)
            if energy >= 3:
                # Prioritize Ragavan for pump (4/3 flying with combat triggers is devastating)
                ragavans = [a for a in attackers if a.name == RAGAVAN]
                non_flyers = [a for a in attackers if not has_keyword(a, 'flying')]
                if ragavans:
                    target = ragavans[0]
                elif non_flyers:
                    target = max(non_flyers, key=lambda c: safe_power(c))
                else:
                    target = max(attackers, key=lambda c: safe_power(c))
                gs.energy = energy - 3
                target.counters += 2  # +2/+2
                gs._log(f"  Guide pump: {target.name} gets +2/+2 flying ({gs.energy}E left)")
        
        # Phlage attack trigger: "Whenever Phlage enters or ATTACKS, deals 3 to any target + 3 life"
        # This fires EVERY attack, not just ETB. Massive damage over multiple turns.
        phlages_attacking = [a for a in attackers if a.name == PHLAGE]
        if phlages_attacking:
            for p in phlages_attacking:
                # 3 damage to best opponent creature or face
                if opponent:
                    opp_creatures = [c for c in opponent.zones.battlefield
                                     if not c.is_land() and c.has(Tag.CREATURE)]
                    killable = [c for c in opp_creatures if safe_toughness(c) <= 3]
                    if killable:
                        kill = max(killable, key=lambda c: safe_power(c))
                        opponent.zones.battlefield.remove(kill)
                        opponent.zones.graveyard.append(kill)
                        gs._log(f"  Phlage attack trigger: kill {kill.name} + 3 life")
                    else:
                        gs.damage_dealt += 3
                        gs._log(f"  Phlage attack trigger: 3 face + 3 life ({gs.damage_dealt} total)")
                else:
                    gs.damage_dealt += 3
                gs.life += 3
                self._gained_life_this_turn = True
        
        return attackers

    def declare_blockers(self, gs: GameState, opponent_gs: GameState,
                         attackers: list) -> dict:
        """
        Block with expendable tokens to preserve life total.
        Use Cat tokens to chump Slickshot/pumped prowess creatures.
        """
        assignments = {}
        if not attackers:
            return assignments

        # Find our available blockers (prefer tokens)
        blockers = [c for c in gs.zones.battlefield
                    if not c.is_land() and c.has(Tag.CREATURE)
                    and not getattr(c, 'tapped', False)]
        tokens = [c for c in blockers if 'Token' in c.name]
        non_tokens = [c for c in blockers if 'Token' not in c.name]

        # Sort attackers by power (block biggest first)
        dangerous = sorted(attackers, key=lambda c: -safe_power(c))

        used_blockers = set()
        for attacker in dangerous:
            atk_power = safe_power(attacker)
            if atk_power < 2:
                continue  # don't waste a blocker on a 1-power creature

            # Flying creatures can only be blocked by flying/reach
            if has_keyword(attacker, 'flying'):
                flying_blockers = [b for b in blockers
                                   if id(b) not in used_blockers
                                   and (has_keyword(b, 'flying') or has_keyword(b, 'reach'))]
                if not flying_blockers:
                    continue  # can't block flying
                blocker = flying_blockers[0]
            else:
                # Prefer tokens for chump blocking
                available_tokens = [b for b in tokens if id(b) not in used_blockers]
                available_non = [b for b in non_tokens if id(b) not in used_blockers]
                if available_tokens:
                    blocker = available_tokens[0]
                elif available_non and atk_power >= 4:
                    # Only trade non-tokens for big threats
                    blocker = min(available_non, key=lambda c: safe_power(c))
                else:
                    continue

            assignments[id(attacker)] = [blocker]
            used_blockers.add(id(blocker))

        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        """Use removal reactively when opponent deploys a threat."""
        if not opponent:
            return None
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures:
            return None

        best = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(best) < 2:
            return None

        # Find castable removal
        for c in gs.zones.hand:
            if c.name == LIGHTNING_BOLT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                if safe_toughness(best) <= 3:
                    return c
        return None

    def end_step_actions(self, gs, opponent):
        """End step — oracle-correct timing for all end-step triggers.
        
        1. Ocelot Pride: "At the beginning of your end step, if you gained life
           this turn, create a 1/1 white Cat creature token." (ONCE per Ocelot)
        2. Mobilize tokens: "Sacrifice them at the beginning of the next end step."
           → Sacrifice to Bombardment FIRST for free damage before forced sacrifice
        3. Goblin Bombardment: sacrifice remaining expendable tokens for face damage
        """
        guides = sum(1 for c in gs.zones.battlefield if c.name == GUIDE_OF_SOULS)
        
        # 1. OCELOT END STEP — one Cat per Ocelot if gained life this turn
        ocelots = sum(1 for c in gs.zones.battlefield if c.name == OCELOT_PRIDE)
        if ocelots > 0 and self._gained_life_this_turn:
            for _ in range(ocelots):
                gs._make_token("Cat Token", "1", "1", "Creature — Cat")
                self._tokens_entered += 1
                # Cat entering triggers Guide
                if guides:
                    gs.life += guides
                    gs.energy = getattr(gs, 'energy', 0) + guides
            gs._log(f"  Ocelot end step: {ocelots} Cat token(s)")
        
        # 2. BOMBARDMENT — sacrifice MOBILIZE tokens (they die anyway) + strategic Cat sac
        # Key insight: Don't sacrifice ALL tokens. Keep Cats for blocking.
        # Only sacrifice Cats deliberately for Ajani transform or when going for lethal.
        has_bombardment = any(c.name == GOBLIN_BOMBARD for c in gs.zones.battlefield)
        ajani_on_board = [c for c in gs.zones.battlefield if c.name == AJANI]
        cat_died = False
        
        if has_bombardment:
            # ONLY sacrifice Mobilize tokens (they're forced to die at end step anyway)
            bombard_dmg = self._mobilize_tokens
            
            if bombard_dmg > 0:
                gs.damage_dealt += bombard_dmg
                gs._log(f"  Bombardment: sac {bombard_dmg} Mobilize tokens → {bombard_dmg} face ({gs.damage_dealt} total)")
        
        # 2b. Deliberately sacrifice ONE Cat to trigger Ajani transform
        # Only if Ajani is on board AND we have 2+ creatures to benefit from PW pump
        # AND we have a Cat to sacrifice
        if ajani_on_board and not self._ajani_pw_active and has_bombardment:
            our_creatures = sum(1 for c in gs.zones.battlefield
                                if not c.is_land() and c.has(Tag.CREATURE))
            cat_tokens = [c for c in gs.zones.battlefield
                          if 'Cat' in getattr(c, 'name', '') and 'Token' in getattr(c, 'name', '')]
            if cat_tokens and our_creatures >= 3:
                # Worth transforming — sacrifice Cat for Ajani PW + 1 Bombardment damage
                t = cat_tokens[0]
                gs.zones.battlefield.remove(t)
                gs.zones.graveyard.append(t)
                gs.damage_dealt += 1
                cat_died = True
                gs._log(f"  Sac Cat → Ajani transform + 1 Bombardment dmg")
        
        # 2c. AJANI TRANSFORM — Cat died + Ajani on board → flip to planeswalker
        if cat_died and ajani_on_board and not self._ajani_pw_active:
            aj = ajani_on_board[0]
            gs.zones.battlefield.remove(aj)
            gs.zones.exile.append(aj)
            self._ajani_pw_active = True
            self._ajani_pw_loyalty = 4
            gs._log(f"  AJANI TRANSFORMS → Ajani, Resilient Leader (Loyalty 4)")
        
        # 3. Forced Mobilize sacrifice (if no Bombardment, tokens just die)
        # (Already removed from battlefield if Bombardment ate them above)
        
        # Reset per-turn trackers
        self._mobilize_tokens = 0
        
        # Ragavan Treasure — each Ragavan that attacked and wasn't blocked = Treasure
        # Oracle: "Whenever Ragavan deals combat damage to a player, create a Treasure token"
        from engine.keywords import KWTag
        ragavans = sum(1 for c in gs.zones.battlefield
                       if c.name == RAGAVAN
                       and not getattr(c, 'summoning_sickness', False))
        if ragavans > 0:
            self._treasures += ragavans
            gs._log(f"  Ragavan: +{ragavans} Treasure(s) ({self._treasures} total)")

    def _play_land_if_able(self, gs: GameState):
        """Play best land. Fetchland/shockland life costs handled by engine automatically."""
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        def score(c):
            n = c.name.lower()
            if 'mesa' in n or 'strand' in n or 'marsh' in n or 'heath' in n:
                return 0  # fetchlands first (fix mana)
            if 'foundry' in n:
                return 1  # shockland
            if 'arena' in n:
                return 2
            if 'parlor' in n:
                return 3
            return 4
        best = min(lands, key=score)
        gs.play_land(best)
