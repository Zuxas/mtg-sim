# Auto-generated match APL for Grixis Discard (standard) by Gemma 4
# Date: 2026-04-19
# Validated: Valid: 25.0% WR

"""Match APL for Grixis Discard (Standard).
This deck leverages discard triggers (FOMO, Agatha's Soul Cauldron) and tempo plays
to generate card advantage and burn damage.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

# Card name constants
ABRADE = "Abrade"
AGATHAS_SOUL_CAULDRON = "Agatha's Soul Cauldron"
FEAR_OF_MISSING_OUT = "Fear of Missing Out"
INTO_THE_FLOOD_MAW = "Into the Flood Maw"
ISLAND = "Island"
MARAUDING_MAKO = "Marauding Mako"
MOUNTAIN = "Mountain"
MULTIVERSAL_PASSAGE = "Multiversal Passage"
PROFT_S_EIDETIC_MEMORY = "Proft's Eidetic Memory"
QUANTUM_RIDDLER = "Quantum Riddler"
RIVERPYRE_VERGE = "Riverpyre Verge"
SPIREBLUFF_CANAL = "Spirebluff Canal"
STEAMCORE_SCHOLAR = "Steamcore Scholar"
TORCH_THE_TOWER = "Torch the Tower"
VIVI_ORNITIER = "Vivi Ornitier"
WINTERNIGHT_STORIES = "Winternight Stories"

# Interaction/Removal Spells (Sideboard/Core)
ANNUL = "Annul"
DISDAINFUL_STROKE = "Disdainful Stroke"
FRESH_START = "Fresh Start"
OBLITERATING_BOLT = "Obliterating Bolt"
PYROCLASM = "Pyroclasm"
SPELL_PIERCE = "Spell Pierce"

# Helper sets for quick checks
DISCARD_ENGINES = {FEAR_OF_MISSING_OUT, AGATHAS_SOUL_CAULDRON}
TEMPO_INTERACTION = {ABRADE, INTO_THE_FLOOD_MAW, MULTIVERSAL_PASSAGE}
BURN_SPELLS = {TORCH_THE_TOWER, OBLITERATING_BOLT}

class GrixisDiscardMatchAPL(MatchAPL):
    AUTO_GENERATED = True  # flagged for rewrite
    name = "Grixis Discard Tempo"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        # Keep if we have enough interaction and discard engines
        if len(hand) <= 4: return True
        
        # Check for core engines
        has_engine = any(c.name in DISCARD_ENGINES for c in hand)
        has_tempo = any(c.name in TEMPO_INTERACTION for c in hand)
        
        # Must have at least 2 lands and some interaction
        lands = sum(1 for c in hand if c.is_land())
        
        if lands < 2: return False
        
        if has_engine and has_tempo: return True
        
        # Fallback: If we are desperate, keep if we have enough mulligans left
        return mulligans >= 2

    def bottom(self, hand, n):
        # Prioritize lands and key spells
        lands = [c for c in hand if c.is_land()]
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands + spells)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        # 1. Play land and tap
        self._play_land_if_able(gs)
        gs.tap_lands()
        
        # 2. Remove opponent threats (Prioritize removal)
        if opponent:
            self._use_removal(gs, opponent)
        
        # 3. Deploy creatures (If we have mana and value)
        # Sort by CMC to play cheapest first
        hand_creatures = sorted([c for c in gs.zones.hand if c.has(Tag.CREATURE)], 
                                 key=lambda c: c.cmc)
        
        for c in hand_creatures:
            if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
        
        # 4. Burn face/removal (Use burn spells if available)
        hand_burns = sorted([c for c in gs.zones.hand if c.name in BURN_SPELLS], 
                            key=lambda c: c.cmc)
        
        for c in hand_burns:
            if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                # Manual zone moves for non-creature spells
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                
                # Apply burn effects
                gs.damage_dealt += 3
                gs.noncreature_spells_this_turn += 1

    def _use_removal(self, gs, opponent):
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures: return
        
        # Target the biggest threat
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 2: return

        # Check for Abrade/Into the Flood Maw (Artifact/Enchantment removal)
        for c in list(gs.zones.hand):
            if c.name in {ABRADE, INTO_THE_FLOOD_MAW} and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                # Manual zone moves for non-creature spells
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                
                if target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.graveyard.append(target)
                return

        # Check for other removal (e.g., if we had a specific counterspell)
        # Since we only have burn/artifact removal, we stop here.
        pass

    def declare_attackers(self, gs, opponent):
        # Attack with all available creatures
        return [c for c in gs.zones.battlefield
                if c.has(Tag.CREATURE) and not c.is_land()
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        # No specific blocking strategy, let the game engine handle it
        return {}

    def respond_to_spell(self, gs, opponent, spell):
        # Respond with counterspells if available
        hand_spells = [c for c in gs.zones.hand if c.name in {ANNUL, DISDAINFUL_STROKE, SPELL_PIERCE}]
        
        # Simple response: counter the most expensive spell we can afford
        if hand_spells:
            # Sort by CMC descending to hit the biggest threat
            hand_spells.sort(key=lambda c: getattr(c, 'cmc', 0), reverse=True)
            
            # Check if the spell is a threat (e.g., high CMC)
            if getattr(spell, 'cmc', 0) > 0 and gs.mana_pool.can_cast(hand_spells[0].mana_cost, hand_spells[0].cmc):
                # Assume we counter the spell
                c = hand_spells[0]
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                return c
        return None

    def end_step_actions(self, gs, opponent):
        # No specific end step actions
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        
        # Play the first available land
        gs.play_land(lands[0])