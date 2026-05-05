# Auto-generated match APL for Esper Pixie (standard) by Gemma 4
# Date: 2026-04-19
# Validated: Valid: 48.0% WR

from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

# Card name constants
CECIL = "Cecil, Dark Knight"
NURTURING_PIXIE = "Nurturing Pixie"
SPYGLASS_SIREN = "Spyglass Siren"
KAITO = "Kaito, Bane of Nightmares"
MOMENTUM_BREAKER = "Momentum Breaker"
COSMOGRAND_ZENITH = "Cosmogrand Zenith"
TRAGIC_TRAJECTORY = "Tragic Trajectory"
SUNPEARL_KIRIN = "Sunpearl Kirin"
BLEACHBONE_VERGE = "Bleachbone Verge"
CONCEALED_COURTYARD = "Concealed Courtyard"
FLOODFARM_VERGE = "Floodfarm Verge"
GLOOMLAKE_VERGE = "Gloomlake Verge"
GODLESS_SHRINE = "Godless Shrine"
ISLAND = "Island"
SWAMP = "Swamp"
STARTING_TOWN = "Starting Town"
TINYBONES_JOINS_UP = "Tinybones Joins Up"
WATERY_GRAVE = "Watery Grave"
NOWHERE_TO_RUN = "Nowhere to Run"
STORMCHASERS_TALENT = "Stormchaser's Talent"

# Core threats/synergy pieces
PIXIE_THREATS = {NURTURING_PIXIE, SPYGLASS_SIREN}
KEY_CREATURES = {CECIL, KAITO, MOMENTUM_BREAKER, COSMOGRAND_ZENITH, SUNPEARL_KIRIN}

class EsperPixieMatchAPL(MatchAPL):
    AUTO_GENERATED = True  # flagged for rewrite
    name = "Esper Pixie Tempo"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        # Keep hands with early threats and interaction
        if len(hand) <= 4: return True
        
        # Check for early threats (Pixies/Siren)
        has_early_threat = any(c.name in PIXIE_THREATS for c in hand)
        
        # Check for interaction (removal/utility)
        has_interaction = any(c.name in [CECIL, MOMENTUM_BREAKER, TRAGIC_TRAJECTORY] for c in hand)
        
        if has_early_threat and has_interaction: return True
        
        # Fallback: If we have decent land count and some threats
        lands = sum(1 for c in hand if c.is_land())
        creatures = sum(1 for c in hand if c.name in PIXIE_THREATS)
        
        if lands >= 2 and creatures >= 1: return True
        
        return mulligans >= 2

    def bottom(self, hand, n):
        # Prioritize keeping lands and key spells
        lands = [c for c in hand if c.is_land()]
        spells = [c for c in hand if c.name in KEY_CREATURES or c.name in [CECIL, MOMENTUM_BREAKER, TRAGIC_TRAJECTORY]]
        
        # Sort spells by CMC (ascending) to keep early plays
        spells.sort(key=lambda c: c.cmc)
        
        # Combine and take the top N
        return (lands + spells)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        # 1. Play land and tap
        self._play_land_if_able(gs)
        gs.tap_lands()
        
        # 2. Remove opponent threats
        if opponent:
            self._use_removal(gs, opponent)
        
        # 3. Stormchaser's Talent — {U} enchantment, draws cards
        for c in list(gs.zones.hand):
            if c.name == STORMCHASERS_TALENT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Stormchaser's Talent: card draw engine")
                break

        # 4. Deploy creatures by CMC (Prioritize low cost threats)
        # Iterate over a copy since we might modify gs.zones.hand
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and c.name in KEY_CREATURES and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
        
        # 4. Deploy low-cost synergy pieces (Pixies/Siren)
        for c in list(gs.zones.hand):
            if c.name in PIXIE_THREATS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def _use_removal(self, gs, opponent):
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures: return
        
        # Target the biggest threat
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 2: return
        
        # Nowhere to Run: {1}{B}, -3/-3 enchantment on a creature
        for c in list(gs.zones.hand):
            if c.name != NOWHERE_TO_RUN: continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc): continue
            if safe_toughness(target) <= 3:
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                gs.noncreature_spells_this_turn += 1
                if target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.graveyard.append(target)
                gs._log(f"  Nowhere to Run: -3/-3 kills {target.name}")
                return

        # Check for available removal spells in hand
        removal_spells = [c for c in gs.zones.hand
                           if c.name in [CECIL, MOMENTUM_BREAKER, TRAGIC_TRAJECTORY]
                           and gs.mana_pool.can_cast(c.mana_cost, c.cmc)]

        if not removal_spells: return

        # Use the first available removal spell
        spell_to_use = removal_spells[0]

        # Execute removal
        gs.mana_pool.pay(spell_to_use.mana_cost, spell_to_use.cmc)

        # Remove target from opponent's battlefield and put it in our graveyard
        if target in opponent.zones.battlefield:
            opponent.zones.battlefield.remove(target)
            gs.zones.graveyard.append(target)

        # Move the spell used to the graveyard
        gs.zones.hand.remove(spell_to_use)
        gs.zones.graveyard.append(spell_to_use)


    def declare_attackers(self, gs, opponent):
        # Attack with all available creatures
        return [c for c in gs.zones.battlefield
                if c.has(Tag.CREATURE) and not c.is_land()
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        # No complex blocking strategy needed; let the board state dictate trades.
        return {}

    def respond_to_spell(self, gs, opponent, spell):
        # No complex interaction needed; rely on proactive removal.
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        gs.play_land(lands[0])