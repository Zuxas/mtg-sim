"""
apl/boros_aggro_standard_match.py — Match-aware Boros Aggro APL (Standard)

Boros Aggro deck:
1. T1 Kumano Faces Kakkazan (saga: +1/+1, pings, then 2/2 haste) or Swiftspear
2. Charming Scoundrel: T2 haste, treasure or rummage
3. Phoenix Chick: flying haste, recurs from graveyard
4. Goddric: 4/4 celebrant (first nontoken creature = 3/3 haste dragon)
5. Squee: 2/1 haste, creates 1/1 goblin tokens on attack
6. Lightning Strike / Play with Fire: removal or face burn
7. Monstrous Rage / Witchstalker Frenzy: pump and board control
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

# Card name constants
SWIFTSPEAR          = "Monastery Swiftspear"
KUMANO              = "Kumano Faces Kakkazan"
PHOENIX_CHICK       = "Phoenix Chick"
CHARMING_SCOUNDREL  = "Charming Scoundrel"
GODDRIC             = "Goddric, Cloaked Reveler"
SQUEE               = "Squee, Dubious Monarch"
BLOODTHIRSTY_ADV    = "Bloodthirsty Adversary"
LIGHTNING_STRIKE    = "Lightning Strike"
PLAY_WITH_FIRE      = "Play with Fire"
MONSTROUS_RAGE      = "Monstrous Rage"
WITCHSTALKER_FRENZY = "Witchstalker Frenzy"
FELDON              = "Feldon, Ronom Excavator"
VOLDAREN_EPICURE    = "Voldaren Epicure"

ONE_DROPS = {SWIFTSPEAR, KUMANO, PHOENIX_CHICK, VOLDAREN_EPICURE}
BURN_SPELLS = {LIGHTNING_STRIKE, PLAY_WITH_FIRE}
REMOVAL_SPELLS = {LIGHTNING_STRIKE, PLAY_WITH_FIRE, WITCHSTALKER_FRENZY}


class BorosAggroStandardMatchAPL(MatchAPL):
    name = "Boros Aggro (Standard)"
    win_condition_damage = 20
    max_turns = 8

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        ones = sum(1 for c in hand if c.name in ONE_DROPS)
        burns = sum(1 for c in hand if c.name in BURN_SPELLS)
        creatures = sum(1 for c in hand if c.has(Tag.CREATURE))
        if lands == 0:
            return False
        if lands > 4:
            return False
        # Need a T1 play
        if ones >= 1 and lands >= 1:
            return True
        if lands >= 2 and creatures >= 1 and burns >= 1:
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
        """Boros aggro: deploy hasty threats, burn face or remove blockers."""
        self._play_land_if_able(gs)
        gs.tap_lands()

        # 1. Removal on opponent's biggest creature
        if opponent:
            self._try_removal(gs, opponent)

        # 2. Deploy one-drops (haste priority)
        for name in (SWIFTSPEAR, KUMANO, PHOENIX_CHICK):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # 2b. Voldaren Epicure (1-drop, creates blood token)
        for c in list(gs.zones.hand):
            if c.name == VOLDAREN_EPICURE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Voldaren Epicure ETB: create Blood token")
                break

        # 3. Charming Scoundrel (T2 haste + treasure/rummage)
        for c in list(gs.zones.hand):
            if c.name == CHARMING_SCOUNDREL and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 4. Bloodthirsty Adversary (2/2 haste, can recast burn from GY)
        for c in list(gs.zones.hand):
            if c.name == BLOODTHIRSTY_ADV and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 5. Squee (2/1 haste, creates goblin tokens)
        for c in list(gs.zones.hand):
            if c.name == SQUEE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 5b. Feldon, Ronom Excavator (creature, cast when mana available)
        for c in list(gs.zones.hand):
            if c.name == FELDON and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 6. Goddric (4/4, celebrant = 3/3 haste dragon)
        for c in list(gs.zones.hand):
            if c.name == GODDRIC and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 7. Pump spells pre-combat (prowess triggers)
        my_creatures = [x for x in gs.zones.battlefield
                        if not x.is_land() and x.has(Tag.CREATURE)]
        if my_creatures:
            for c in list(gs.zones.hand):
                if c.name == MONSTROUS_RAGE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.noncreature_spells_this_turn += 1
                    gs._log(f"  Monstrous Rage (pump + prowess)")
                    break

        # 8. Burn face with remaining mana
        for c in list(gs.zones.hand):
            if c.name not in BURN_SPELLS:
                continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                continue
            dmg = 3 if c.name == LIGHTNING_STRIKE else 2
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
        """Use Lightning Strike / Play with Fire / Witchstalker Frenzy on threats."""
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
            elif c.name == PLAY_WITH_FIRE:
                dmg = 2
            elif c.name == WITCHSTALKER_FRENZY:
                dmg = 4  # Frenzy deals 4 to creature
            else:
                dmg = 2
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
