"""apl/amulet_titan.py — Amulet Titan APL (Modern)
Amulet of Vigor + bounce lands → accelerate to 6 mana → Primeval Titan T3.
Combo: Amulet in play + Simic Growth Chamber = 2 mana from one land drop.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState

TITAN       = "Primeval Titan"
AMULET      = "Amulet of Vigor"
GRAZER      = "Arboreal Grazer"
SPELUNKING  = "Spelunking"
RUMBLE      = "Malevolent Rumble"
SAGA        = "Urza's Saga"
ZENITH      = "Green Sun's Zenith"
PACT        = "Summoner's Pact"
SCAPESHIFT  = "Scapeshift"
LOTUS_FIELD = "Lotus Field"

class AmuletTitanAPL(SBPlanMixin, BaseAPL):
    name = "Amulet Titan"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands   = sum(1 for c in hand if c.is_land())
        has_amulet = any(c.name == AMULET for c in hand)
        has_titan  = any(c.name in {TITAN, ZENITH, PACT} for c in hand)
        has_ramp   = any(c.name in {GRAZER, SPELUNKING, RUMBLE} for c in hand)
        if lands == 0: return False
        if lands >= 2 and (has_titan or has_amulet): return True
        if lands >= 1 and has_amulet and has_ramp: return True
        return len(hand) <= 5 or mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[4:][:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        # Deploy Amulet first (enables all bounce land tricks)
        for card in list(gs.hand()):
            if card.name == AMULET and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
        # Ramp spells
        for name in (GRAZER, SPELUNKING, RUMBLE, SAGA):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        # The win condition
        for name in (TITAN, ZENITH, SCAPESHIFT):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    if card.name == TITAN:
                        # Titan ETB: fetch 2 lands, deal 6+ damage
                        gs.damage_dealt += 6
                        gs._log("  Primeval Titan ETB → 6 trample damage")
                    break
        # Summoner's Pact to find Titan
        for card in list(gs.hand()):
            if card.name == PACT and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                token = gs._make_token("Primeval Titan", "6", "6", "Creature")
                gs.damage_dealt += 6
                gs._log("  Summoner's Pact → Primeval Titan")
                break
