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

        # 2. REMOVAL FIRST — kill their threats before they combo
        if opponent:
            self._use_removal_on_creatures(gs, opponent)

        # 3. Deploy lifegain engine creatures (priority order)
        # Guide of Souls is #1 — every creature entering = +1 life +1 energy
        for name in (GUIDE_OF_SOULS, OCELOT_PRIDE, AJANI):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
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

        # 7. Fill remaining mana with creatures
        while True:
            castable = [c for c in gs.zones.hand
                        if c.has(Tag.CREATURE)
                        and c.name not in REMOVAL_SPELLS
                        and gs.mana_pool.can_cast(c.mana_cost, c.cmc)]
            if not castable:
                break
            card = min(castable, key=lambda c: (c.cmc, c.name))
            if not gs.cast_spell(card):
                break
            guides = sum(1 for x in gs.zones.battlefield if x.name == GUIDE_OF_SOULS)
            if guides:
                gs.life += guides
                gs.energy = getattr(gs, 'energy', 0) + guides
                self._gained_life_this_turn = True

        # 8. Simulate end-step Ocelot tokens
        self._simulate_end_step(gs)

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
        if opponent has removal mana open."""
        from engine.keywords import KWTag
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land() or c.name == GOBLIN_BOMBARD:
                continue
            if getattr(c, 'summoning_sickness', False):
                continue
            if getattr(c, 'tapped', False):
                continue
            attackers.append(c)
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
        """Nothing special at opponent's end step."""
        pass

    def _play_land_if_able(self, gs: GameState):
        """Play best land."""
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        def score(c):
            n = c.name.lower()
            if 'mesa' in n or 'strand' in n or 'marsh' in n or 'heath' in n:
                return 0
            if 'foundry' in n:
                return 1
            if 'arena' in n:
                return 2
            if 'parlor' in n:
                return 3
            return 4
        best = min(lands, key=score)
        gs.play_land(best)
