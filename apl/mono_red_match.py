"""
apl/mono_red_match.py — Match-aware Mono Red Aggro APL (Modern)

Match changes from goldfish:
1. Bolt lifegain creatures (Guide of Souls, Ocelot) on sight — they compound
2. Searing Blaze is LIVE (landfall + creature target = 3 to creature + 3 face)
3. Skullcrack prevents opponent lifegain for a turn
4. Eidolon of the Great Revel punishes both players — deploy when ahead on life
5. Otherwise: burn face, burn face, burn face
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

GOBLIN_GUIDE  = "Goblin Guide"
SWIFTSPEAR    = "Monastery Swiftspear"
EIDOLON       = "Eidolon of the Great Revel"
BOLT          = "Lightning Bolt"
CHAIN         = "Chain Lightning"
RIFT_BOLT     = "Rift Bolt"
SEARING_BLAZE = "Searing Blaze"
SKULLCRACK    = "Skullcrack"
LIGHT_UP      = "Light Up the Stage"
PRICE         = "Price of Progress"
FIREBLAST     = "Fireblast"
LAVA_SPIKE    = "Lava Spike"

ONE_DROPS = {GOBLIN_GUIDE, SWIFTSPEAR}
BURN_FACE = {BOLT, CHAIN, RIFT_BOLT, LAVA_SPIKE, PRICE, FIREBLAST, SKULLCRACK}
# Creatures we MUST kill because they gain life
LIFEGAIN_THREATS = {"Guide of Souls", "Ocelot Pride", "Phlage, Titan of Fire's Fury"}


class MonoRedMatchAPL(MatchAPL):
    name = "Mono Red Aggro"
    win_condition_damage = 20
    max_turns = 8

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        ones = sum(1 for c in hand if c.name in ONE_DROPS)
        burns = sum(1 for c in hand if c.name in BURN_FACE)
        if lands == 0: return False
        if lands <= 1 and ones + burns >= 4: return True
        if lands >= 2 and (ones >= 1 or burns >= 2): return True
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
        """Burn deck: deploy cheap threats, bolt lifegain creatures, burn face."""
        self._play_land_if_able(gs)

        # 1. Kill lifegain creatures ON SIGHT — they compound every turn
        if opponent:
            self._kill_lifegain(gs, opponent)

        # 2. Deploy one-drops (haste = attack this turn)
        for name in (GOBLIN_GUIDE, SWIFTSPEAR):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # 3. Eidolon — deploy when we're ahead on life or racing
        if opponent:
            life_diff = gs.life - opponent.life
            if life_diff >= 0 or gs.life >= 14:
                for c in list(gs.zones.hand):
                    if c.name == EIDOLON and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        gs.cast_spell(c)
                        break

        # 4. Searing Blaze — live in match (landfall + creature target)
        if opponent and gs.land_played:
            opp_creatures = [c for c in opponent.zones.battlefield
                             if not c.is_land() and c.has(Tag.CREATURE)]
            if opp_creatures:
                target = max(opp_creatures, key=lambda c: safe_power(c))
                for c in list(gs.zones.hand):
                    if c.name == SEARING_BLAZE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        gs.mana_pool.pay(c.mana_cost, c.cmc)
                        gs.zones.hand.remove(c)
                        gs.zones.graveyard.append(c)
                        gs.damage_dealt += 3  # 3 to face with landfall
                        gs.noncreature_spells_this_turn += 1
                        if safe_toughness(target) <= 3 and target in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(target)
                            opponent.zones.graveyard.append(target)
                        gs._log(f"  Searing Blaze: 3 face + 3 to {target.name}")
                        break

        # 5. Burn face — ALL of it
        for c in list(gs.zones.hand):
            if c.name not in BURN_FACE:
                continue
            if c.name == FIREBLAST:
                # Sacrifice two Mountains instead of paying mana
                mountains = [m for m in gs.zones.battlefield
                             if 'mountain' in (m.type_line or '').lower()]
                if len(mountains) >= 2:
                    for m in mountains[:2]:
                        gs.zones.battlefield.remove(m)
                        gs.zones.graveyard.append(m)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.damage_dealt += 4
                    gs._log(f"  Fireblast (sac 2 Mountains): 4 face ({gs.damage_dealt})")
                continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                continue
            dmg = 4 if c.name == PRICE else 3
            gs.mana_pool.pay(c.mana_cost, c.cmc)
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            gs.damage_dealt += dmg
            gs.noncreature_spells_this_turn += 1
            gs._log(f"  {c.name} face: {dmg} ({gs.damage_dealt} total)")

        # 6. Remaining creatures
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)


    def _kill_lifegain(self, gs: GameState, opponent: GameState):
        """Kill lifegain creatures immediately — they compound."""
        targets = [c for c in opponent.zones.battlefield
                   if not c.is_land() and c.name in LIFEGAIN_THREATS]
        if not targets:
            return
        target = targets[0]  # kill first one found
        if safe_toughness(target) <= 3:
            for c in list(gs.zones.hand):
                if c.name == BOLT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.noncreature_spells_this_turn += 1
                    if target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.graveyard.append(target)
                    gs._log(f"  Bolt → kill {target.name} (lifegain threat)")
                    return

    def declare_attackers(self, gs, opponent):
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land(): continue
            if getattr(c, 'summoning_sickness', False): continue
            if getattr(c, 'tapped', False): continue
            if c.has(Tag.CREATURE):
                attackers.append(c)
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        return {}  # burn never blocks — race or die

    def respond_to_spell(self, gs, opponent, spell):
        return None  # no interaction

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        gs.play_land(lands[0])
