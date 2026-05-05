# Auto-generated match APL for Izzet Cauldron (standard) by Gemma 4
# Date: 2026-04-19
# Validated: Valid: 26.0% WR

"""Match APL for Izzet Cauldron (Standard).
This deck is a tempo/midrange strategy focused on generating card advantage and applying consistent burn damage.
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
FIRE_MAGIC = "Fire Magic"
INTO_THE_FLOOD_MAW = "Into the Flood Maw"
ISLAND = "Island"
MARAUDING_MAKO = "Marauding Mako"
MOUNTAIN = "Mountain"
PROFT_S_EIDETIC_MEMORY = "Proft's Eidetic Memory"
QUANTUM_RIDDLER = "Quantum Riddler"
RIVERPYRE_VERGE = "Riverpyre Verge"
SOULSTONE_SANCTUARY = "Soulstone Sanctuary"
SPIREBLUFF_CANAL = "Spirebluff Canal"
STARTING_TOWN = "Starting Town"
STEAMCORE_SCHOLAR = "Steamcore Scholar"
TERSA_LIGHTSHATTER = "Tersa Lightshatter"
THUNDERING_FALLS = "Thundering Falls"
TORCH_THE_TOWER = "Torch the Tower"
VIVI_ORNITIER = "Vivi Ornitier"
WILD_RIDE = "Wild Ride"
WINTERNIGHT_STORIES = "Winternight Stories"

# Helper sets for quick checks
LANDS = {ISLAND, MOUNTAIN, RIVERPYRE_VERGE, SPIREBLUFF_CANAL, STARTING_TOWN, THUNDERING_FALLS}
DRAW_ENGINES = {FEAR_OF_MISSING_OUT, PROFT_S_EIDETIC_MEMORY}
VALUE_ENGINES = {AGATHAS_SOUL_CAULDRON, STEAMCORE_SCHOLAR}
REMOVAL = {ABRADE, INTO_THE_FLOOD_MAW, TORCH_THE_TOWER}
THREATS = {MARAUDING_MAKO, VIVI_ORNITIER}
BURN_SPELLS = {FIRE_MAGIC, TERSA_LIGHTSHATTER, WILD_RIDE}


class IzzetCauldronMatchAPL(MatchAPL):
    AUTO_GENERATED = True  # flagged for rewrite
    name = "Izzet Cauldron Tempo"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        # Keep hands with early interaction, draw engines, and lands.
        if len(hand) <= 4: return True
        
        lands = sum(1 for c in hand if c.is_land())
        
        # Check for a mix of resources
        if lands >= 1 and any(c.name in DRAW_ENGINES for c in hand): return True
        if lands >= 2 and any(c.name in REMOVAL for c in hand): return True
        
        # If we have few lands, we need strong spells
        if lands < 1 and len(hand) >= 3 and any(c.name in VALUE_ENGINES for c in hand): return True
        
        return mulligans >= 2

    def bottom(self, hand, n):
        # Prioritize lands and high-impact spells (removal/draw)
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

        # 2. Removal (Prioritize hitting non-land permanents)
        if opponent:
            self._use_removal(gs, opponent)

        # 3. Card Advantage/Value Engines (FOMO, Proft's, Cauldron, Scholar)
        # Try to cast the most impactful engines first
        for c in list(gs.zones.hand):
            if c.name in DRAW_ENGINES and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
            elif c.name in VALUE_ENGINES and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

        # 4. Deploy Threats (Scholar, Mako, Cauldron, etc.)
        for c in list(gs.zones.hand):
            if c.name in THREATS or c.name == STEAMCORE_SCHOLAR:
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)

        # 5. Interaction/Burn (Use remaining mana)
        for c in list(gs.zones.hand):
            if c.name in REMOVAL and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                # Use removal spells
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                self._handle_removal_cast(gs, opponent, c)
                
            elif c.name in BURN_SPELLS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                # Use burn spells
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                gs.damage_dealt += 3
                gs.noncreature_spells_this_turn += 1

    def _handle_removal_cast(self, gs, opponent, spell):
        # Check if the spell is Abrade or Into the Flood Maw
        if spell.name == ABRADE or spell.name == INTO_THE_FLOOD_MAW:
            # Target the biggest non-land permanent
            targets = [c for c in opponent.zones.battlefield
                       if not c.is_land() and c.name not in ["Island", "Mountain", "Riverpyre Verge", "Spirebluff Canal", "Starting Town", "Thundering Falls"]]
            if not targets: return

            target = max(targets, key=lambda c: safe_power(c) + safe_toughness(c))
            
            if target in opponent.zones.battlefield:
                opponent.zones.battlefield.remove(target)
                opponent.zones.graveyard.append(target)

    def _use_removal(self, gs, opponent):
        # Prioritize hitting non-land permanents
        if opponent:
            # Find the best target (highest power/toughness non-land)
            targets = [c for c in opponent.zones.battlefield
                       if not c.is_land() and c.name not in ["Island", "Mountain", "Riverpyre Verge", "Spirebluff Canal", "Starting Town", "Thundering Falls"]]
            if not targets: return

            target = max(targets, key=lambda c: safe_power(c) + safe_toughness(c))
            
            # Attempt to cast removal spells
            for spell_name in [ABRADE, INTO_THE_FLOOD_MAW]:
                spell = next((c for c in gs.zones.hand if c.name == spell_name), None)
                if spell and gs.mana_pool.can_cast(spell.mana_cost, spell.cmc):
                    self._handle_removal_cast(gs, opponent, spell)
                    return # Only use one removal spell per turn for simplicity

    def declare_attackers(self, gs, opponent):
        # Attack with all available creatures
        return [c for c in gs.zones.battlefield
                if c.has(Tag.CREATURE) and not c.is_land()
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        # Proactive tempo deck, only block if necessary to save a key permanent or prevent immediate loss.
        # For simplicity, we assume we are not blocking unless absolutely forced.
        return {}

    def respond_to_spell(self, gs, opponent, spell):
        # Respond with removal if the opponent targets a key permanent or threat.
        
        # Check if the opponent is trying to remove a major threat (e.g., Scholar, Cauldron)
        threats = [c for c in gs.zones.battlefield if c.name in VALUE_ENGINES or c.name == STEAMCORE_SCHOLAR]
        if not threats: return None

        # Check if we have removal available
        for spell_name in [ABRADE, INTO_THE_FLOOD_MAW]:
            spell = next((c for c in gs.zones.hand if c.name == spell_name), None)
            if spell and gs.mana_pool.can_cast(spell.mana_cost, spell.cmc):
                # Assume the spell targets the incoming spell/creature
                return spell
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        gs.play_land(lands[0])