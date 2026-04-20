"""
apl/mono_red_aggro_standard_match.py — Match-aware Mono Red Aggro APL (Standard)

Mono Red hasty threats + burn:
1. Hired Claw: 2/1 haste for 1
2. Emberheart Challenger: 2/2 haste for RR, draw on attack
3. Burnout Bashtronaut: hasty creature
4. Razorkin Needlehead: pings opponent on ETB
5. Screaming Nemesis: 3/3 haste, when it takes damage opponent takes same
6. Nova Hellkite: flying haste dragon finisher
7. Burst Lightning / Lightning Strike / Shock: removal or face burn
8. Witchstalker Frenzy: board sweeper for small creatures
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

# Card name constants
HIRED_CLAW          = "Hired Claw"
EMBERHEART          = "Emberheart Challenger"
BURNOUT_BASHTRONAUT = "Burnout Bashtronaut"
RAZORKIN_NEEDLEHEAD = "Razorkin Needlehead"
SCREAMING_NEMESIS   = "Screaming Nemesis"
NOVA_HELLKITE       = "Nova Hellkite"
BURST_LIGHTNING     = "Burst Lightning"
LIGHTNING_STRIKE    = "Lightning Strike"
SHOCK               = "Shock"
WITCHSTALKER_FRENZY = "Witchstalker Frenzy"
OBLITERATING_BOLT   = "Obliterating Bolt"
SUNSPINE_LYNX       = "Sunspine Lynx"

ONE_DROPS = {HIRED_CLAW}
BURN_SPELLS = {BURST_LIGHTNING, LIGHTNING_STRIKE, SHOCK, OBLITERATING_BOLT}
REMOVAL_SPELLS = {BURST_LIGHTNING, LIGHTNING_STRIKE, SHOCK, WITCHSTALKER_FRENZY, OBLITERATING_BOLT}


class MonoRedAggroStandardMatchAPL(MatchAPL):
    name = "Mono Red Aggro (Standard)"
    win_condition_damage = 20
    max_turns = 8

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        creatures = sum(1 for c in hand if c.has(Tag.CREATURE))
        burns = sum(1 for c in hand if c.name in BURN_SPELLS)
        if lands == 0:
            return False
        if lands > 4:
            return False
        # Need 2-3 lands and early creatures
        if lands >= 2 and lands <= 3 and creatures >= 1:
            return True
        if lands >= 2 and burns >= 2:
            return True
        if lands == 1 and creatures >= 2:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        pool = lands[3:] + spells
        return pool[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """Mono red aggro: deploy hasty threats, burn blockers, burn face."""
        self._play_land_if_able(gs)
        gs.tap_lands()

        # 1. Removal on opponent's biggest creature before developing
        if opponent:
            self._try_removal(gs, opponent)

        # 2. Deploy one-drops (Hired Claw = 2/1 haste)
        for c in list(gs.zones.hand):
            if c.name == HIRED_CLAW and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 3. Emberheart Challenger (2/2 haste, draw on attack)
        for c in list(gs.zones.hand):
            if c.name == EMBERHEART and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 4. Burnout Bashtronaut (hasty creature)
        for c in list(gs.zones.hand):
            if c.name == BURNOUT_BASHTRONAUT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 5. Razorkin Needlehead (pings on ETB)
        for c in list(gs.zones.hand):
            if c.name == RAZORKIN_NEEDLEHEAD and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                # Simulate ETB ping
                gs.damage_dealt += 1
                gs._log(f"  Razorkin Needlehead ETB: 1 ping ({gs.damage_dealt} total)")
                break

        # 6. Screaming Nemesis (3/3 haste — mirrors damage to opponent)
        for c in list(gs.zones.hand):
            if c.name == SCREAMING_NEMESIS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 7. Nova Hellkite (flying haste dragon finisher)
        for c in list(gs.zones.hand):
            if c.name == NOVA_HELLKITE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 7b. Sunspine Lynx (creature, cast when able)
        for c in list(gs.zones.hand):
            if c.name == SUNSPINE_LYNX and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 8. Burn face with remaining mana
        for c in list(gs.zones.hand):
            if c.name not in BURN_SPELLS:
                continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                continue
            if c.name == LIGHTNING_STRIKE:
                dmg = 3
            elif c.name == OBLITERATING_BOLT:
                dmg = 3
            elif c.name == BURST_LIGHTNING:
                dmg = 2  # base mode; kicked = 4 but unlikely early
            else:
                dmg = 2  # Shock
            gs.mana_pool.pay(c.mana_cost, c.cmc)
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            gs.damage_dealt += dmg
            gs.noncreature_spells_this_turn += 1
            gs._log(f"  {c.name} face: {dmg} ({gs.damage_dealt} total)")

        # 9. Any remaining creatures
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def _try_removal(self, gs: GameState, opponent: GameState):
        """Use burn on opponent's biggest creature."""
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures:
            return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 2:
            return
        for c in list(gs.zones.hand):
            if c.name not in REMOVAL_SPELLS:
                continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                continue
            # Determine damage
            if c.name == LIGHTNING_STRIKE:
                dmg = 3
            elif c.name == OBLITERATING_BOLT:
                dmg = 3
            elif c.name == WITCHSTALKER_FRENZY:
                dmg = 4
            elif c.name == BURST_LIGHTNING:
                dmg = 2
            else:
                dmg = 2  # Shock
            if dmg < safe_toughness(target):
                continue
            gs.mana_pool.pay(c.mana_cost, c.cmc)
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            gs.noncreature_spells_this_turn += 1
            if target in opponent.zones.battlefield:
                opponent.zones.battlefield.remove(target)
                opponent.zones.graveyard.append(target)
            gs._log(f"  {c.name} -> kill {target.name}")
            return

    def declare_attackers(self, gs, opponent):
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land():
                continue
            if getattr(c, 'summoning_sickness', False):
                continue
            if getattr(c, 'tapped', False):
                continue
            if c.has(Tag.CREATURE):
                attackers.append(c)
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        return {}  # aggro never blocks — race or die

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        gs.play_land(lands[0])
