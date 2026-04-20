# Auto-generated match APL for Four Color Overlords (standard) by Gemma 4
# Date: 2026-04-19
# Validated: Valid: 16.0% WR

from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

# Card name constants
CAVERN_OF_SOULS = "Cavern of Souls"
FLOODFARM_VERGE = "Floodfarm Verge"
FOREST = "Forest"
GET_LOST = "Get Lost"
HEDGE_MAZE = "Hedge Maze"
HERD_MIGRATION = "Herd Migration"
HUSHWOOD_VERGE = "Hushwood Verge"
ISLAND = "Island"
LEYLINE_BINDING = "Leyline Binding"
LUSH_PORTICO = "Lush Portico"
METICULOUS_ARCHIVE = "Meticulous Archive"
OVERLORD_OF_THE_FLOODPITS = "Overlord of the Floodpits"
OVERLORD_OF_THE_HAUNTWOODS = "Overlord of the Hauntwoods"
OVERLORD_OF_THE_MISTMOORS = "Overlord of the Mistmoors"
PLAINS = "Plains"
SCROLLSHIFT = "Scrollshift"
SHADOWY_BACKSTREET = "Shadowy Backstreet"
SUNFALL = "Sunfall"
SWAMP = "Swamp"
TEMPORARY_LOCKDOWN = "Temporary Lockdown"
UP_THE_BEANSTALK = "Up the Beanstalk"
ZUR_ETERNAL_SCHEMER = "Zur, Eternal Schemer"

# Helper sets for quick checks
LANDS = {
    CAVERN_OF_SOULS, FLOODFARM_VERGE, FOREST, HUSHWOOD_VERGE, ISLAND,
    LUSH_PORTICO, PLAINS, SHADOWY_BACKSTREET, SWAMP
}

CORE_THREATS = {
    OVERLORD_OF_THE_HAUNTWOODS, OVERLORD_OF_THE_FLOODPITS,
    OVERLORD_OF_THE_MISTMOORS, ZUR_ETERNAL_SCHEMER
}

INTERACTION_SPELLS = {
    GET_LOST, LEYLINE_BINDING, TEMPORARY_LOCKDOWN, SCROLLSHIFT, SUNFALL,
    METICULOUS_ARCHIVE, HERD_MIGRATION
}

class FourColorOverlordsMatchAPL(MatchAPL):
    name = "Four Color Overlords"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        # Keepable Hand: 2-3 lands, 1-2 early threats (T1/T2), and at least one interaction spell.
        
        lands = [c for c in hand if c.is_land()]
        
        # Count early threats (T1/T2)
        early_threats = [c for c in hand if c.name in CORE_THREATS and c.cmc <= 2]
        
        # Count interaction spells
        interaction_count = sum(1 for c in hand if c.name in INTERACTION_SPELLS)

        if len(hand) <= 4: return True
        
        # Check for minimum requirements
        if len(lands) < 2: return False
        if len(early_threats) < 1: return False
        if interaction_count < 1: return False
        
        return True

    def bottom(self, hand, n):
        # Sort by CMC (ascending) and then by name (alphabetical)
        def sort_key(c):
            return (getattr(c, 'cmc', 999), c.name)
        
        sorted_hand = sorted(hand, key=sort_key)
        return sorted_hand[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        # 1. Play land and tap
        self._play_land_if_able(gs)
        gs.tap_lands()
        
        # 2. Remove opponent threats (Prioritize board wipes/mass removal)
        if opponent:
            self._use_removal(gs, opponent)
        
        # 3. Deploy threats and ramp (Prioritize low CMC, high impact)
        # Sort hand by CMC to ensure we play the cheapest threats first
        hand_list = list(gs.zones.hand)
        hand_list.sort(key=lambda c: getattr(c, 'cmc', 999))
        
        for c in hand_list:
            if c.name in CORE_THREATS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
            elif c.name == UP_THE_BEANSTALK and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
            elif c.name == ZUR_ETERNAL_SCHEMER and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
        
        # 4. Use remaining interaction/utility spells
        for c in list(gs.zones.hand):
            if c.name in INTERACTION_SPELLS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                # Special handling for non-creature spells
                if c.name == GET_LOST:
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    # Get Lost is a board wipe, handled by the engine, but we ensure it's cast.
                    gs.cast_spell(c) 
                elif c.name == LEYLINE_BINDING:
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    # Leyline Binding requires targeting, which the engine handles on cast.
                    gs.cast_spell(c)
                elif c.name == TEMPORARY_LOCKDOWN:
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.cast_spell(c)
                elif c.name == SCROLLSHIFT:
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.cast_spell(c)
                elif c.name == SUNFALL:
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.cast_spell(c)
                elif c.name == METICULOUS_ARCHIVE:
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.cast_spell(c)
                elif c.name == HERD_MIGRATION:
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.cast_spell(c)


    def _use_removal(self, gs, opponent):
        # Identify the biggest threat on the opponent's board
        opp_creatures = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land()]
        
        if not opp_creatures: return
        
        # Target the creature with the highest power
        target = max(opp_creatures, key=lambda c: safe_power(c))
        
        if safe_power(target) < 2: return

        # Attempt to use the best removal spell available
        removal_spells = [c for c in list(gs.zones.hand) 
                           if c.name in INTERACTION_SPELLS and c.name != GET_LOST]
        
        if not removal_spells: return

        # Prioritize Leyline Binding or Temporary Lockdown if they can hit the target
        for c in removal_spells:
            if c.name == LEYLINE_BINDING and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                # Assume the engine handles targeting the biggest threat
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                gs.cast_spell(c)
                return
            
            if c.name == TEMPORARY_LOCKDOWN and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                gs.cast_spell(c)
                return
        
        # Fallback: Use any other available removal spell
        for c in removal_spells:
            if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                gs.cast_spell(c)
                return


    def declare_attackers(self, gs, opponent):
        # All non-land, non-tapped creatures are attackers
        return [c for c in gs.zones.battlefield
                if c.has(Tag.CREATURE) and not c.is_land()
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        # No specific blocking strategy implemented, return empty dict
        return {}

    def respond_to_spell(self, gs, opponent, spell):
        # No specific interaction response implemented
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        # Play the first available land
        gs.play_land(lands[0])