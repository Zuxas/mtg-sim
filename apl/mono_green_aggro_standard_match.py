"""
apl/mono_green_aggro_standard_match.py -- Mono Green Aggro/Landfall match APL (Standard)

Guide sources (Decktionary Mar 2026, mtg.cardsrealm Mar 2026):
Threat sequencing:
  T1-2: ramp dorks (Llanowar Elves, Badgermole Cub)
  T2-3: engine pieces (Earthbender Ascension {1GG}, Icetill Explorer {2G}, Sapling Nursery {2G})
  T3-4: finishers (Sazh's Chocobo {1G}, Mightform Harmonizer {3G}, Mossborn Hydra {4G})
  Win:  Mightform Harmonizer + Leatherhead combo, or token flood via Sapling Nursery

Trade logic:
  - Stack counters on threats, give trample (Earthbender Ascension), attack face
  - Trade only small dorks (Llanowar Elves); preserve Chocobo, Harmonizer, Hydra
  - Protect hexproof creatures (Leatherhead) at all costs; use Snakeskin Veil
  - Sapling Nursery tokens = blockers in grindy games, not attackers

Combat tricks:
  Snakeskin Veil {G}: hexproof + +1/+1 counter (hold up {G} when in hand)
  Escape Tunnel {1G}: land + phasing = combat trick for unblockable swing
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from apl.aware_match_apl import AwareMatchAPL
from apl.mono_green_aggro_standard import MonoGreenAggroAPL

SNAKESKIN_VEIL    = "Snakeskin Veil"
MOSSBORN_HYDRA    = "Mossborn Hydra"
MIGHTFORM         = "Mightform Harmonizer"
LEATHERHEAD       = "Leatherhead, Swamp Stalker"
EARTHBENDER       = "Earthbender Ascension"
SAPLING_NURSERY   = "Sapling Nursery"
MELTSTRIDER       = "Meltstrider's Resolve"
SURRAK            = "Surrak, Elusive Hunter"
TORPOR_ORB        = "Torpor Orb"


class MonoGreenAggroStandardMatchAPL(AwareMatchAPL, MonoGreenAggroAPL):
    ARCHETYPE = "aggro"

    # No counters; but hold {G} for Snakeskin Veil when a key threat is in play
    COUNTER_COST  = 0
    COUNTER_CARDS = set()

    MATCH_REMOVAL = {}   # no instant removal in mono-green main deck
    MATCH_EXILE   = set()

    SB_PLANS = {
        "aggro": (
            # vs Red/Burn: Meltstrider's Resolve (life gain); Mossborn Hydra closes faster
            [MOSSBORN_HYDRA, MOSSBORN_HYDRA, MELTSTRIDER, MELTSTRIDER],
            ["Eumidian Terrabotanist", "Eumidian Terrabotanist", SAPLING_NURSERY, SAPLING_NURSERY],
        ),
        "control": (
            # vs Control/Jeskai: Surrak + Mossborn Hydra; cut slow tokens
            [MOSSBORN_HYDRA, MOSSBORN_HYDRA, SURRAK, SURRAK],
            ["Eumidian Terrabotanist", "Eumidian Terrabotanist", MIGHTFORM, MIGHTFORM],
        ),
        "combo": (
            # vs Izzet Lessons: Mossborn Hydra closes before they assemble engine
            [MOSSBORN_HYDRA, MOSSBORN_HYDRA, MOSSBORN_HYDRA, MOSSBORN_HYDRA],
            [SAPLING_NURSERY, SAPLING_NURSERY, "Eumidian Terrabotanist", "Eumidian Terrabotanist"],
        ),
        "tempo": (
            # vs Izzet Prowess/Spellementals: Torpor Orb stops ETBs; Mossborn for speed
            [TORPOR_ORB, TORPOR_ORB, MOSSBORN_HYDRA, MOSSBORN_HYDRA],
            [SAPLING_NURSERY, SAPLING_NURSERY, "Eumidian Terrabotanist", "Eumidian Terrabotanist"],
        ),
        "midrange": (
            # vs Dimir/Golgari: Surrak (hexproof body) + Mossborn Hydra
            [SURRAK, SURRAK, MOSSBORN_HYDRA, MOSSBORN_HYDRA],
            [SAPLING_NURSERY, SAPLING_NURSERY, "Eumidian Terrabotanist", "slow threats"],
        ),
    }

    # ---------------------------------------------------------------------------
    # reserve_mana: hold {G} for Snakeskin Veil when a key threat is on board
    # ---------------------------------------------------------------------------

    def reserve_mana(self, gs: GameState, opponent: GameState):
        has_veil = any(c.name == SNAKESKIN_VEIL for c in gs.zones.hand)
        if has_veil:
            key_threats = {MIGHTFORM, LEATHERHEAD, MOSSBORN_HYDRA, EARTHBENDER}
            has_key_threat = any(c.name in key_threats for c in gs.zones.battlefield
                                 if c.has(Tag.CREATURE))
            gs.mana_reserve = 1 if has_key_threat else 0
        else:
            gs.mana_reserve = 0
