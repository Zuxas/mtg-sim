"""
apl/gruul_aggro_standard_match.py — Match-aware Gruul Aggro APL (Standard)

Gruul prowess-style aggro deck:
1. T1 Heartfire Hero or Swiftspear (haste)
2. Pump spells (Monstrous Rage, Turn Inside Out) trigger prowess en masse
3. Slickshot Show-Off: flying, prowess, 3-power with any noncreature spell
4. Torch the Tower / Shock as removal OR face burn
5. Snakeskin Veil protects key threats + pumps
6. Emberheart Challenger: 2/2 haste, draw on attack
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

# Card name constants
HEARTFIRE_HERO     = "Heartfire Hero"
SWIFTSPEAR         = "Monastery Swiftspear"
MANIFOLD_MOUSE     = "Manifold Mouse"
EMBERHEART         = "Emberheart Challenger"
SLICKSHOT          = "Slickshot Show-Off"
QUESTING_DRUID     = "Questing Druid"
MONSTROUS_RAGE     = "Monstrous Rage"
TURN_INSIDE_OUT    = "Turn Inside Out"
SHOCK              = "Shock"
TORCH_THE_TOWER    = "Torch the Tower"
SNAKESKIN_VEIL     = "Snakeskin Veil"
INNKEEPERS_TALENT  = "Innkeeper's Talent"
OBLITERATING_BOLT  = "Obliterating Bolt"
SUNSPINE_LYNX      = "Sunspine Lynx"

ONE_DROPS = {HEARTFIRE_HERO, SWIFTSPEAR}
PUMP_SPELLS = {MONSTROUS_RAGE, TURN_INSIDE_OUT, SNAKESKIN_VEIL}
BURN_SPELLS = {SHOCK, TORCH_THE_TOWER, OBLITERATING_BOLT}
REMOVAL_SPELLS = {SHOCK, TORCH_THE_TOWER, OBLITERATING_BOLT}


class GruulAggroStandardMatchAPL(MatchAPL):
    name = "Gruul Aggro (Standard)"
    win_condition_damage = 20
    max_turns = 8

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        creatures = sum(1 for c in hand if c.has(Tag.CREATURE))
        pumps = sum(1 for c in hand if c.name in PUMP_SPELLS)
        burns = sum(1 for c in hand if c.name in BURN_SPELLS)
        if lands == 0:
            return False
        if lands >= 4:
            return False
        # Need a creature + action
        if creatures >= 1 and (pumps + burns >= 1):
            return True
        if lands <= 2 and creatures >= 2:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        pool = lands[2:] + spells
        return pool[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """Prowess aggro: deploy threats, pump, burn."""
        self._play_land_if_able(gs)
        gs.tap_lands()

        # 1. Removal on opponent's biggest creature first
        if opponent:
            self._try_removal(gs, opponent)

        # 2. Deploy one-drops (haste creatures first)
        for name in (HEARTFIRE_HERO, SWIFTSPEAR):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # 3. Deploy Manifold Mouse (menace + pump)
        for c in list(gs.zones.hand):
            if c.name == MANIFOLD_MOUSE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 4. Emberheart Challenger (2/2 haste, draw on attack)
        for c in list(gs.zones.hand):
            if c.name == EMBERHEART and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 5. Slickshot Show-Off (flying prowess)
        for c in list(gs.zones.hand):
            if c.name == SLICKSHOT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 6. Innkeeper's Talent (enchantment value)
        for c in list(gs.zones.hand):
            if c.name == INNKEEPERS_TALENT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 7. Questing Druid
        for c in list(gs.zones.hand):
            if c.name == QUESTING_DRUID and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 7b. Sunspine Lynx (creature, cast when able)
        for c in list(gs.zones.hand):
            if c.name == SUNSPINE_LYNX and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 8. Pump spells — cast pre-combat to trigger prowess
        for name in (MONSTROUS_RAGE, TURN_INSIDE_OUT):
            my_creatures = [x for x in gs.zones.battlefield
                            if not x.is_land() and x.has(Tag.CREATURE)]
            if not my_creatures:
                break
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.noncreature_spells_this_turn += 1
                    gs._log(f"  {c.name} (pump + prowess trigger)")
                    break

        # 9. Burn face with remaining mana
        for c in list(gs.zones.hand):
            if c.name not in BURN_SPELLS:
                continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                continue
            dmg = 3 if c.name == OBLITERATING_BOLT else 2  # Bolt = 3, Shock/Torch = 2
            gs.mana_pool.pay(c.mana_cost, c.cmc)
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            gs.damage_dealt += dmg
            gs.noncreature_spells_this_turn += 1
            gs._log(f"  {c.name} face: {dmg} ({gs.damage_dealt} total)")

        # 10. Any remaining creatures
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def _try_removal(self, gs: GameState, opponent: GameState):
        """Use Shock/Torch on opponent's biggest creature."""
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
            dmg = 3 if c.name == OBLITERATING_BOLT else 2  # Bolt = 3, Shock/Torch = 2
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
        return {}  # aggro never blocks — race

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        gs.play_land(lands[0])
