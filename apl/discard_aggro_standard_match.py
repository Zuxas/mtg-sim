"""
apl/discard_aggro_standard_match.py -- Discard Aggro match APL (Mardu/Rakdos/Boros, Standard)

Shared match layer for all three discard-payoff aggro shells.

Game plan: T1 payoff (Iron-Shield Elf/Mako), T2 discard enabler (Cool but Rude/Practiced Offense),
Bloodghast recurs on every land drop. Monument to Endurance if included = incidental drain.
Kill around T4-6 via creature damage + discard recursion.

Matchup roles:
  vs Aggro:    race with recurring threats (Bloodghast never stays dead)
  vs Control:  discard disrupts their hand; Bloodghast dodges sweepers
  vs Midrange: out-recurse with Bloodghast + Flamewake Phoenix; discard stax their hand
  vs Combo:    apply pressure before they assemble; Soul-Guide Lantern from SB
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from apl.aware_match_apl import AwareMatchAPL
from apl.discard_aggro_standard import DiscardAggroAPL, MarduDiscardAPL, RakdosDiscardAPL, BorosDiscardAPL

BLOODGHAST   = "Bloodghast"
IRON_SHIELD  = "Iron-Shield Elf"
MAKO         = "Marauding Mako"
FLAMEWAKE    = "Flamewake Phoenix"
CASEY        = "Casey Jones, Vigilante"
COOL_RUDE    = "Cool but Rude"
PRACTICED    = "Practiced Offense"

SOUL_GUIDE   = "Soul-Guide Lantern"
DURESS       = "Duress"
PYROCLASM    = "Pyroclasm"
CASE_CRIMSON = "Case of the Crimson Pulse"

KILL_PRIORITY = (
    "Mightform Harmonizer",    # Combo kill piece; kills before it fires
    "Gran-Gran",               # Monument enabler
    "Icetill Explorer",        # Landfall chain engine
)


class DiscardAggroStandardMatchAPL(AwareMatchAPL, DiscardAggroAPL):
    name = "Discard Aggro"
    ARCHETYPE = "aggro"

    # No counterspells; all-in on threats
    COUNTER_COST  = 0
    COUNTER_CARDS = set()
    MATCH_REMOVAL = {}
    MATCH_EXILE   = set()

    SB_PLANS = {
        "aggro": (
            # vs Red/Aggro: Pyroclasm sweeps their side, Bloodghast survives (doesn't have 2 toughness)
            [PYROCLASM, PYROCLASM, CASE_CRIMSON, CASE_CRIMSON],
            [COOL_RUDE, COOL_RUDE, PRACTICED, PRACTICED],
        ),
        "control": (
            # vs Control: Duress hits counters/sweepers; Soul-Guide vs reanimation
            [DURESS, DURESS, DURESS, DURESS, SOUL_GUIDE],
            [PYROCLASM, PYROCLASM, CASE_CRIMSON, CASE_CRIMSON, PRACTICED],
        ),
        "combo": (
            # vs Combo/Lessons: Soul-Guide Lantern; Duress strips key pieces
            [SOUL_GUIDE, SOUL_GUIDE, SOUL_GUIDE, DURESS, DURESS, DURESS],
            [PYROCLASM, PYROCLASM, CASE_CRIMSON, CASE_CRIMSON, COOL_RUDE, PRACTICED],
        ),
        "ramp": (
            # vs Landfall: apply pressure; their ground creatures can't outrace Bloodghast
            [DURESS, DURESS, CASE_CRIMSON, CASE_CRIMSON],
            [PYROCLASM, PYROCLASM, COOL_RUDE, PRACTICED],
        ),
        "tempo": (
            # vs Izzet Prowess: Duress strips pump; race with recurring threats
            [DURESS, DURESS, DURESS, PYROCLASM, PYROCLASM],
            [COOL_RUDE, COOL_RUDE, PRACTICED, CASE_CRIMSON, CASE_CRIMSON],
        ),
    }

    def reserve_mana(self, gs: GameState, opponent: GameState):
        gs.mana_reserve = 0   # tap out every turn


class MarduDiscardStandardMatchAPL(DiscardAggroStandardMatchAPL, MarduDiscardAPL):
    name = "Mardu Discard"


class RakdosDiscardStandardMatchAPL(DiscardAggroStandardMatchAPL, RakdosDiscardAPL):
    name = "Rakdos Discard"


class BorosDiscardStandardMatchAPL(DiscardAggroStandardMatchAPL, BorosDiscardAPL):
    name = "Boros Discard"
