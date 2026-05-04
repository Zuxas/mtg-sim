"""
apl/temur_lute_standard_match.py -- Temur Lute match APL (Standard 2026)

Nicolas Cosgrove PT SOS list. Spell-heavy combo-control.

Decklist core:
  Resonating Lute {1U}:         enchantment; tutors instants/sorceries from deck
  Consult the Star Charts {1U}: scry 3 / draw 2 (Learn)
  Great Hall of the Biblioplex: land that tutors Lessons
  Flashback {2UR}:              recur instant/sorcery from GY
  Colorstorm Stallion {1UR}:    3/3 haste; +1/+1 per spell cast this turn (Prowess-like)
  Three Steps Ahead {U}+:       counter mode costs +{1U}; copy mode +{1U}
  Doppelgang {XGU}:             copy X target permanents (explosive with Stallion)
  Sear {1R}:                    instant 4 damage (primary removal)
  Prismari Charm {UR}:          discard/draw or deal 2 damage

Sideboard: Ghost Vacuum, Negate, Slagstorm, Annul, Flashfreeze, Soul-Guide Lantern

Role vs matchups:
  vs Aggro/Tempo:  control -- Sear + Prismari Charm stabilize; Slagstorm from SB
  vs Landfall:     control -- counter Harmonizer/Ascension; Flashfreeze from SB
  vs Izzet Lessons: combo race -- chain Lute tutors faster than their Monument engine
  vs Control:      tempo -- Doppelgang copies Stallion for explosive damage burst
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from engine.match_state import safe_toughness
from apl.aware_match_apl import AwareMatchAPL
from apl.lute_control_standard import LuteControlAPL

THREE_STEPS = "Three Steps Ahead"
NEGATE      = "Negate"
ANNUL       = "Annul"
FLASHFREEZE = "Flashfreeze"
SPELL_PIERCE = "Spell Pierce"
SEAR        = "Sear"
TRAUMATIC   = "Traumatic Critique"
PRISMARI    = "Prismari Charm"
SLAGSTORM   = "Slagstorm"
GHOST_VAC   = "Ghost Vacuum"
SOUL_GUIDE  = "Soul-Guide Lantern"
FIRE_MAGIC  = "Fire Magic"
DISDAINFUL  = "Disdainful Stroke"
IMPRACTICAL = "Impractical Joke"
STALLION    = "Colorstorm Stallion"
DOPPELGANG  = "Doppelgang"
LUTE        = "Resonating Lute"
EMERITUS    = "Emeritus of Ideation"

# Permanents to Annul on the stack
ANNUL_TARGETS = {
    "Monument to Endurance",
    "Artist's Talent",
    "Stormchaser's Talent",
    "Earthbender Ascension",
    "Sapling Nursery",
}

KILL_PRIORITY = (
    "Gran-Gran",          # Monument enabler; kill before it loots
    "Badgermole Cub",     # Ramp; Sear kills it
    "Icetill Explorer",   # Landfall chain engine
    "Mightform Harmonizer", # Combo kill piece
)


class TemurLuteStandardMatchAPL(AwareMatchAPL, LuteControlAPL):
    name = "Temur Lute"
    ARCHETYPE = "combo"

    # Hold {1U} for Three Steps Ahead counter mode
    COUNTER_COST  = 2
    COUNTER_CARDS = {THREE_STEPS, NEGATE, ANNUL, FLASHFREEZE, SPELL_PIERCE}

    MATCH_REMOVAL = {
        SEAR:     ("1R", 4),   # 4 damage instant — main removal
        TRAUMATIC: ("1U", 3),  # 3 damage (discount if blue in hand)
        PRISMARI:  ("UR", 2),  # 2 damage mode
    }
    MATCH_EXILE = set()

    SB_PLANS = {
        "aggro": (
            # vs Izzet Prowess/Spellementals: Slagstorm + Fire Magic sweep
            [SLAGSTORM, SLAGSTORM, FIRE_MAGIC, FIRE_MAGIC, NEGATE],
            [DOPPELGANG, DOPPELGANG, DOPPELGANG, EMERITUS, EMERITUS],
        ),
        "control": (
            # vs Control: Negate + Disdainful; race with Stallion + Doppelgang
            [NEGATE, NEGATE, DISDAINFUL, DISDAINFUL, IMPRACTICAL],
            [GHOST_VAC, GHOST_VAC, SOUL_GUIDE, SEAR, SEAR],
        ),
        "combo": (
            # vs Izzet Lessons: Annul Monument/Artist's Talent; GY hate
            [ANNUL, ANNUL, SOUL_GUIDE, GHOST_VAC, GHOST_VAC, NEGATE],
            [DOPPELGANG, DOPPELGANG, DOPPELGANG, PRISMARI, PRISMARI, EMERITUS],
        ),
        "ramp": (
            # vs Landfall: Flashfreeze + Slagstorm + counter payoffs
            [FLASHFREEZE, FLASHFREEZE, SLAGSTORM, SLAGSTORM, DISDAINFUL],
            [DOPPELGANG, EMERITUS, PRISMARI, PRISMARI, IMPRACTICAL],
        ),
        "tempo": (
            # vs tempo: removal + counters; Stallion closes fast
            [SLAGSTORM, SLAGSTORM, NEGATE, NEGATE, ANNUL],
            [DOPPELGANG, DOPPELGANG, EMERITUS, PRISMARI, PRISMARI],
        ),
    }

    def reserve_mana(self, gs: GameState, opponent: GameState):
        has_counter = any(c.name in self.COUNTER_CARDS for c in gs.zones.hand)
        has_removal = any(c.name in self.MATCH_REMOVAL for c in gs.zones.hand)
        if has_counter:
            gs.mana_reserve = self.COUNTER_COST
        elif has_removal:
            gs.mana_reserve = 2
        else:
            gs.mana_reserve = 0

    def pre_combat_instant(self, gs: GameState, opponent: GameState):
        opp_creatures = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land()]

        # Slagstorm: sweep when 3+ small creatures (toughness <= 3)
        small = [c for c in opp_creatures if safe_toughness(c) <= 3]
        if len(small) >= 3:
            for card in gs.zones.hand:
                if card.name == SLAGSTORM and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.mana_pool.pay(card.mana_cost, card.cmc)
                    gs.zones.hand.remove(card)
                    gs.zones.graveyard.append(card)
                    for victim in list(small):
                        if victim in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(victim)
                            opponent.zones.graveyard.append(victim)
                    gs._log(f"  [pre-combat] Slagstorm swept {len(small)} creatures")
                    return

        for name in KILL_PRIORITY:
            for c in opp_creatures:
                if c.name == name:
                    if self._kill_with_removal(gs, opponent, c):
                        gs._log(f"  [pre-combat] killed {c.name}")
                        return

        super().pre_combat_instant(gs, opponent)
