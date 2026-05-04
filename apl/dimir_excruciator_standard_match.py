"""
apl/dimir_excruciator_standard_match.py -- Dimir Midrange/Excruciator match APL (Standard)

Victor Santos Esquici 3.1% PT SOS field. Dimir midrange control shell.
Key cards (from RIW Hobbies guide Feb 2026):
  Requiting Hex {1B}: instant removal, better than Stab/Tragic Trajectory; kills creature lands
  Deep-Cavern Bat {1B}: early tempo and hand disruption
  Spell Snare {U}: answers Get Lost, protects Kaito, stops Badgermole Cub
  Excruciator of Sins: recursive threat (self-recurs from graveyard)

Matchup roles:
  vs Aggro:    removal-heavy tempo; run full 4x Requiting Hex
  vs Midrange: interactive midrange; kill creature lands (Restless Reef) aggressively
  vs Control:  tempo threat density; Quantum Riddler scales in long game
  vs Combo:    disruption-first; hand disruption + counter suite
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from engine.match_state import safe_toughness
from apl.aware_match_apl import AwareMatchAPL
from apl.generic_apl import GenericAPL

REQUITING_HEX    = "Requiting Hex"
SPELL_SNARE      = "Spell Snare"
FLASHFREEZE      = "Flashfreeze"
STRATEGIC_BETRAY = "Strategic Betrayal"
QUANTUM_RIDDLER  = "Quantum Riddler"
DEEP_CAVERN_BAT  = "Deep-Cavern Bat"
KAITO            = "Kaito, Bane of Nightmares"
ANNUL            = "Annul"

# Creature lands that must be killed aggressively
CREATURE_LANDS = {"Restless Reef", "Restless Anchorage", "Faerie Mastermind"}

# Removal targets in kill-priority order
KILL_PRIORITY = {
    "Badgermole Cub",       # ramp must die T1-T2
    "Gran-Gran",            # Monument engine enabler
    "Icetill Explorer",     # landfall chain engine
    "Mightform Harmonizer", # combo kill piece
    "Earthbender Ascension",# trample enabler
}


class DimirExcruciatorStandardMatchAPL(AwareMatchAPL, GenericAPL):
    ARCHETYPE = "midrange"

    # Spell Snare = {U}; hold 2 mana for Requiting Hex responses
    COUNTER_COST  = 2
    COUNTER_CARDS = {SPELL_SNARE, FLASHFREEZE}

    MATCH_REMOVAL = {
        REQUITING_HEX: ("1B", None),   # no toughness cap — kills anything at instant speed
    }
    MATCH_EXILE = set()   # no exile removal in main package

    # Sideboard plans from RIW Hobbies Dimir Midrange guide (Aug-Sep 2025)
    # Key: Floodpits Drowner is weak (Fire Magic kills it); cut it first vs red
    # Tishana's Tidebinder shuts ETB/activated abilities -- key SB piece vs ETB-heavy decks
    # The End = exile removal with cost reduction; primary answer to Nova Hellkite
    SB_PLANS = {
        "aggro": (
            # vs Mono Red: cut Floodpits Drowner (Fire Magic), trim Kaito; +removal and lifegain
            ["Tishana's Tidebinder", "Tishana's Tidebinder", "The End", "The End",
             STRATEGIC_BETRAY, STRATEGIC_BETRAY, "Stab"],
            [DEEP_CAVERN_BAT, DEEP_CAVERN_BAT, DEEP_CAVERN_BAT, DEEP_CAVERN_BAT,
             KAITO, KAITO, "Floodpits Drowner"],
        ),
        "tempo": (
            # vs Izzet Prowess/tempo: Tidebinder shuts ETBs; trim Drowner; add interaction
            ["Tishana's Tidebinder", "Tishana's Tidebinder", "The End", "The End",
             STRATEGIC_BETRAY, STRATEGIC_BETRAY],
            [DEEP_CAVERN_BAT, DEEP_CAVERN_BAT, DEEP_CAVERN_BAT, DEEP_CAVERN_BAT,
             KAITO, "Floodpits Drowner"],
        ),
        "control": (
            # vs Azorius Control: counters + Tidebinder; remove slow main-deck pieces
            [FLASHFREEZE, FLASHFREEZE, "Spell Pierce", "Spell Pierce",
             "Disdainful Stroke", "Disdainful Stroke",
             "Tishana's Tidebinder", "Tishana's Tidebinder", ANNUL],
            ["Floodpits Drowner", "Floodpits Drowner", "Floodpits Drowner",
             "Tragic Trajectory", "Tragic Trajectory",
             "Shoot the Sheriff", STRATEGIC_BETRAY],
        ),
        "combo": (
            # vs Izzet Cauldron/combo: GY hate; Annul for enchantments
            ["Ghost Vacuum", "Ghost Vacuum",
             "Tishana's Tidebinder", "Tishana's Tidebinder",
             "The End", "The End", STRATEGIC_BETRAY, STRATEGIC_BETRAY, ANNUL],
            ["Floodpits Drowner", "Floodpits Drowner", "Floodpits Drowner",
             "Tragic Trajectory", "Tragic Trajectory",
             "Sunset Saboteur", "Enduring Curiosity", KAITO, "Floodpits Drowner"],
        ),
        "midrange": (
            # vs Dimir Mirror: Tidebinder + The End; cut Deep-Cavern Bat (weak in mirror)
            ["Tishana's Tidebinder", "Tishana's Tidebinder", "The End", "Stab"],
            [DEEP_CAVERN_BAT, DEEP_CAVERN_BAT, DEEP_CAVERN_BAT, KAITO],
        ),
    }

    def __init__(self):
        GenericAPL.__init__(self, deck_name="Dimir Excruciator", role="midrange")

    # ---------------------------------------------------------------------------
    # Reserve mana: hold 2 for Requiting Hex (instant speed) + Spell Snare
    # ---------------------------------------------------------------------------

    def reserve_mana(self, gs: GameState, opponent: GameState):
        has_hex    = any(c.name == REQUITING_HEX for c in gs.zones.hand)
        has_snare  = any(c.name == SPELL_SNARE   for c in gs.zones.hand)
        if has_hex:
            gs.mana_reserve = 2   # {1}{B} = 2 mana
        elif has_snare:
            gs.mana_reserve = 1   # {U} = 1 mana
        else:
            gs.mana_reserve = 0

    # ---------------------------------------------------------------------------
    # Pre-combat: Requiting Hex priority targets
    # ---------------------------------------------------------------------------

    def pre_combat_instant(self, gs: GameState, opponent: GameState):
        opp_creatures = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land()]

        # Kill creature lands aggressively (Restless Reef can't be bounced)
        for c in opponent.zones.battlefield:
            if c.name in CREATURE_LANDS and c.has(Tag.CREATURE):
                if self._kill_with_removal(gs, opponent, c):
                    gs._log(f"  [pre-combat] killed creature land {c.name}")
                    return

        # Kill priority creatures in order
        for name in KILL_PRIORITY:
            for c in opp_creatures:
                if c.name == name:
                    if self._kill_with_removal(gs, opponent, c):
                        gs._log(f"  [pre-combat] Requiting Hex killed {c.name}")
                        return

        super().pre_combat_instant(gs, opponent)
