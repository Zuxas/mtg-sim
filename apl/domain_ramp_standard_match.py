"""
apl/domain_ramp_standard_match.py — Domain Ramp APL (Standard)

Ramp into haymakers. Fix mana with basics, count domain for cost reduction.
T1-2: Ramp (Courier's Briefcase for treasure)
T3: Topiary Stomper (3/4 body + ramp)
T3-4: Leyline Binding (exile anything, cheap with domain)
T4-5: Sunfall (wrath + incubator token)
T5+: Archangel of Wrath (4/4 flying + 2 dmg ETB), Atraxa (7/7 flying + draw 4-5)
Herd Migration: domain 5 = five 3/3 tokens
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

TOPIARY_STOMPER     = "Topiary Stomper"
COURIERS_BRIEFCASE  = "Courier's Briefcase"
LEYLINE_BINDING     = "Leyline Binding"
SUNFALL             = "Sunfall"
ARCHANGEL_OF_WRATH  = "Archangel of Wrath"
ATRAXA              = "Atraxa, Grand Unifier"
HERD_MIGRATION      = "Herd Migration"
INVASION_ZENDIKAR   = "Invasion of Zendikar"
VIRTUE_PERSISTENCE  = "Virtue of Persistence"
GO_FOR_THE_THROAT   = "Go for the Throat"
DEPOPULATE          = "Depopulate"

RAMP_SPELLS = {TOPIARY_STOMPER, COURIERS_BRIEFCASE, INVASION_ZENDIKAR}
HAYMAKERS   = {ARCHANGEL_OF_WRATH, ATRAXA, HERD_MIGRATION, VIRTUE_PERSISTENCE}


class DomainRampStandardMatchAPL(MatchAPL):
    ARCHETYPE = "ramp"
    SB_PLANS = {
        "aggro": (
            ["1 Destroy Evil", "1 Farewell", "1 Path of Peril",
             "1 Obstinate Baloth", "1 Temporary Lockdown"],
            ["2 Duress", "3 Disdainful Stroke"],
        ),
        "control": (
            ["3 Disdainful Stroke", "2 Duress", "2 Knockout Blow",
             "2 The Cruelty of Gix"],
            ["1 Depopulate", "4 Sunfall", "2 Go for the Throat",
             "2 Archangel of Wrath"],
        ),
        "combo": (
            ["3 Disdainful Stroke", "2 Duress", "1 Shadow Prophecy"],
            ["2 Archangel of Wrath", "2 Go for the Throat", "2 Virtue of Persistence"],
        ),
        "ramp": (
            ["3 Disdainful Stroke", "2 Duress", "1 Farewell"],
            ["2 Go for the Throat", "1 Depopulate", "2 Archangel of Wrath",
             "1 Herd Migration"],
        ),
        "tempo": (
            ["2 Duress", "1 Destroy Evil", "1 Path of Peril",
             "1 Temporary Lockdown"],
            ["2 Archangel of Wrath", "1 Depopulate", "2 Virtue of Persistence"],
        ),
    }
    name = "Domain Ramp Standard"
    win_condition_damage = 20
    max_turns = 15

    def __init__(self):
        self._domain_count = 0
        self._treasure_count = 0

    def _update_domain(self, gs):
        """Count basic land types for domain."""
        types = set()
        for c in gs.zones.battlefield:
            if not c.is_land(): continue
            tl = (getattr(c, 'type_line', '') or '').lower()
            for t in ('plains', 'island', 'swamp', 'mountain', 'forest'):
                if t in tl: types.add(t)
        self._domain_count = len(types)

    def _binding_cost(self):
        """Leyline Binding costs {5}{W} - {1} per domain count. Min {W}."""
        return max(1, 6 - self._domain_count)

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        ramp = sum(1 for c in hand if c.name in RAMP_SPELLS)
        interaction = sum(1 for c in hand if c.name in (LEYLINE_BINDING, SUNFALL))
        if lands < 2: return False
        if lands > 5: return False
        if ramp >= 1 and 3 <= lands <= 4: return True
        if interaction >= 1 and lands >= 3: return True
        if ramp >= 1 and interaction >= 1 and lands >= 2: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        # Keep 3-4 lands, bottom expensive spells first
        return (lands[4:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        """Ramp plan: fix mana, ramp, then deploy haymakers."""
        self._play_land_if_able(gs)
        gs.tap_lands()
        self._update_domain(gs)

        avail = gs.mana_pool.total() + self._treasure_count

        # 1. Courier's Briefcase — treasure token + draw later
        for c in list(gs.zones.hand):
            if c.name == COURIERS_BRIEFCASE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                self._treasure_count += 1
                gs._log(f"  Briefcase: +1 treasure (total {self._treasure_count})")
                avail = gs.mana_pool.total() + self._treasure_count
                break

        # 2. Topiary Stomper — 3/4 body + search for basic land
        for c in list(gs.zones.hand):
            if c.name == TOPIARY_STOMPER and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                # ETB: search for a basic land, put onto battlefield tapped
                gs._log(f"  Stomper: 3/4 + ramp (search basic land)")
                self._update_domain(gs)
                avail = gs.mana_pool.total() + self._treasure_count
                break

        # 3. Invasion of Zendikar — search for basic land
        for c in list(gs.zones.hand):
            if c.name == INVASION_ZENDIKAR and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Invasion of Zendikar: search basic land")
                self._update_domain(gs)
                avail = gs.mana_pool.total() + self._treasure_count
                break

        # 4. Leyline Binding — exile any nonland permanent (domain cost reduction)
        if opponent:
            binding_cost = self._binding_cost()
            opp_threats = [c for c in opponent.zones.battlefield
                           if not c.is_land()]
            if opp_threats:
                target = max(opp_threats, key=lambda c: safe_power(c)
                             if c.has(Tag.CREATURE) else 3)
                for c in list(gs.zones.hand):
                    if c.name == LEYLINE_BINDING and avail >= binding_cost:
                        # Spend treasures if needed
                        mana_needed = binding_cost
                        pool_avail = gs.mana_pool.total()
                        if pool_avail >= mana_needed:
                            gs.mana_pool.flex -= min(mana_needed, gs.mana_pool.flex)
                        else:
                            treasures_needed = mana_needed - pool_avail
                            self._treasure_count -= treasures_needed
                            gs.mana_pool.flex -= min(pool_avail, gs.mana_pool.flex)
                        gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                        c.turn_entered = gs.turn
                        if target in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(target)
                            opponent.zones.exile.append(target)
                        gs._log(f"  Binding: exile {target.name} (cost {binding_cost}, domain={self._domain_count})")
                        avail = gs.mana_pool.total() + self._treasure_count
                        break

        # 5. Go for the Throat — {1}{B}, destroys non-artifact creature
        if opponent:
            opp_creatures = [c for c in opponent.zones.battlefield
                             if not c.is_land() and c.has(Tag.CREATURE)]
            if opp_creatures:
                target = max(opp_creatures, key=lambda c: safe_power(c))
                if safe_power(target) >= 2:
                    for c in list(gs.zones.hand):
                        if c.name == GO_FOR_THE_THROAT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                            gs.mana_pool.pay(c.mana_cost, c.cmc)
                            gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                            gs.noncreature_spells_this_turn += 1
                            if target in opponent.zones.battlefield:
                                opponent.zones.battlefield.remove(target)
                                opponent.zones.graveyard.append(target)
                            gs._log(f"  Go for the Throat: kill {target.name}")
                            avail = gs.mana_pool.total() + self._treasure_count
                            break

        # 6. Depopulate — {2}{W}{W}, destroys all creatures (use when opponent has 3+)
        if opponent:
            opp_creatures = [c for c in opponent.zones.battlefield
                             if not c.is_land() and c.has(Tag.CREATURE)]
            my_creatures = [c for c in gs.zones.battlefield
                            if not c.is_land() and c.has(Tag.CREATURE)]
            if len(opp_creatures) >= 3 and len(my_creatures) <= 1:
                for c in list(gs.zones.hand):
                    if c.name == DEPOPULATE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        gs.mana_pool.pay(c.mana_cost, c.cmc)
                        gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                        gs.noncreature_spells_this_turn += 1
                        total_killed = 0
                        for cr in list(opponent.zones.battlefield):
                            if cr.has(Tag.CREATURE) and not cr.is_land():
                                opponent.zones.battlefield.remove(cr)
                                opponent.zones.graveyard.append(cr)
                                total_killed += 1
                        for cr in list(gs.zones.battlefield):
                            if cr.has(Tag.CREATURE) and not cr.is_land():
                                gs.zones.battlefield.remove(cr)
                                gs.zones.graveyard.append(cr)
                                total_killed += 1
                        gs._log(f"  Depopulate: destroy {total_killed} creatures")
                        avail = gs.mana_pool.total() + self._treasure_count
                        break

        # 7. Sunfall — board wipe + incubator token
        if opponent:
            opp_creatures = [c for c in opponent.zones.battlefield
                             if not c.is_land() and c.has(Tag.CREATURE)]
            my_creatures = [c for c in gs.zones.battlefield
                            if not c.is_land() and c.has(Tag.CREATURE)]
            opp_power = sum(safe_power(c) for c in opp_creatures)
            my_power = sum(safe_power(c) for c in my_creatures)
            # Wrath if opponent has more board presence
            if len(opp_creatures) >= 2 and opp_power > my_power:
                for c in list(gs.zones.hand):
                    if c.name == SUNFALL and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        gs.mana_pool.pay(c.mana_cost, c.cmc)
                        gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                        gs.noncreature_spells_this_turn += 1
                        # Exile all creatures
                        total_exiled = 0
                        for cr in list(opponent.zones.battlefield):
                            if cr.has(Tag.CREATURE) and not cr.is_land():
                                opponent.zones.battlefield.remove(cr)
                                opponent.zones.exile.append(cr)
                                total_exiled += 1
                        for cr in list(gs.zones.battlefield):
                            if cr.has(Tag.CREATURE) and not cr.is_land():
                                gs.zones.battlefield.remove(cr)
                                gs.zones.exile.append(cr)
                                total_exiled += 1
                        gs._log(f"  Sunfall: exile {total_exiled} creatures, make Incubator token")
                        avail = gs.mana_pool.total() + self._treasure_count
                        break

        # 6. Archangel of Wrath — 4/4 flying + 2 damage ETB
        for c in list(gs.zones.hand):
            if c.name == ARCHANGEL_OF_WRATH and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                if opponent:
                    opp_cr = [x for x in opponent.zones.battlefield
                              if not x.is_land() and x.has(Tag.CREATURE)
                              and safe_toughness(x) <= 2]
                    if opp_cr:
                        target = max(opp_cr, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.graveyard.append(target)
                        gs._log(f"  Archangel ETB: 2 dmg kills {target.name}")
                    else:
                        gs.damage_dealt += 2
                        gs._log(f"  Archangel ETB: 2 dmg face")
                else:
                    gs.damage_dealt += 2
                avail = gs.mana_pool.total() + self._treasure_count
                break

        # 7. Atraxa — 7/7 flying, ETB draw ~4 cards (simulated)
        for c in list(gs.zones.hand):
            if c.name == ATRAXA and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Atraxa: 7/7 flying + draw ~4 cards")
                break

        # 8. Herd Migration — domain 5 = five 3/3 beast tokens
        for c in list(gs.zones.hand):
            if c.name == HERD_MIGRATION and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                # Simulate N 3/3 tokens where N = domain count
                token_count = self._domain_count
                gs._log(f"  Herd Migration: {token_count}x 3/3 tokens (domain={self._domain_count})")
                break

        # 9. Virtue of Persistence — graveyard recursion engine
        for c in list(gs.zones.hand):
            if c.name == VIRTUE_PERSISTENCE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Virtue of Persistence: recursion engine online")
                break

        # 10. Remaining castable spells
        for c in list(gs.zones.hand):
            if not c.is_land() and c.has(Tag.CREATURE):
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)

    def declare_attackers(self, gs, opponent):
        """Attack with big threats. Hold Stomper back as blocker early."""
        self._update_domain(gs)
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land(): continue
            if not c.has(Tag.CREATURE): continue
            if getattr(c, 'summoning_sickness', False): continue
            if getattr(c, 'tapped', False): continue
            # Hold Stomper back as blocker early game (great 3/4 body)
            if c.name == TOPIARY_STOMPER and gs.turn <= 5:
                if opponent:
                    opp_cr = [x for x in opponent.zones.battlefield
                              if not x.is_land() and x.has(Tag.CREATURE)]
                    if len(opp_cr) >= 2:
                        continue  # hold back as blocker
            attackers.append(c)
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        """Always block with Stomper (3/4 body is great blocker)."""
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)
                    and not c.is_land() and not getattr(c, 'tapped', False)]
        if not blockers: return assignments

        # Stomper is the ideal blocker — 3/4 trades with most things
        stompers = [b for b in blockers if b.name == TOPIARY_STOMPER]
        biggest_attacker = max(attackers, key=lambda c: safe_power(c))
        if stompers and safe_power(biggest_attacker) <= 4:
            assignments[id(biggest_attacker)] = [stompers[0]]
            return assignments

        # Otherwise block if we survive
        for attacker in sorted(attackers, key=lambda c: safe_power(c), reverse=True):
            for b in blockers:
                if b in [v for vs in assignments.values() for v in vs]:
                    continue
                if safe_toughness(b) > safe_power(attacker):
                    assignments[id(attacker)] = [b]
                    break
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        """Play lands prioritizing color fixing for domain."""
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            # Fetch lands first (fix domain)
            if 'heath' in n or 'flats' in n or 'strand' in n or 'tarn' in n or 'foothills' in n or 'catacombs' in n or 'rainforest' in n: return 0
            # Triomes and duals next (multiple types)
            if 'triome' in n or 'headquarters' in n or "jetmir's garden" in n: return 1
            if 'garden' in n or 'foundry' in n or 'crypt' in n or 'grave' in n: return 2
            # Basics last
            return 4
        gs.play_land(min(lands, key=score))
