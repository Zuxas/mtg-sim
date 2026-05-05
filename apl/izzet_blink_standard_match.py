"""
apl/izzet_blink_standard_match.py -- Izzet Blink match APL (Standard 2026)

PT Lorwyn Eclipsed: 2.0% field (6/306 players). Tyggz decklist.

Prowess + Otter Wizard blink value hybrid. Shares Stormchaser's Talent
engine with Izzet Prowess but replaces burn with blink for card advantage.

Key cards:
  Stormchaser's Talent {1U}:   prowess enchantment (3 noncreature spells = upgrade)
  Thundertrap Trainer {1U}:    Otter Wizard; ETB: look at top 4, take noncreature/nonland
  Splash Portal {U}:           blink target creature. If Otter/Bird/Frog/Rat: draw a card.
                                Combine with Thundertrap Trainer: ETB again + draw = card advantage loop
  Boomerang Basics {U}:        Lesson sorcery; bounce permanent, draw if you controlled it
  Quantum Riddler {2UG}:       ETB scry+draw
  Torch the Tower {R}:         3 damage removal
  Get Out {1R}:                exile removal (instant)
  Frostcliff Siege {1UR}:      enchantment; combat damage = draw (Jeskai mode)
  Ral, Crackling Wit:          planeswalker that copies spells

Sideboard: Annul, Flashfreeze, Ill-Timed Explosion, Into the Flood Maw,
           Disdainful Stroke, Negate, Abrade, Wan Shi Tong Librarian
"""
from __future__ import annotations
from apl.aware_match_apl import AwareMatchAPL
from apl.izzet_prowess_standard import IzzetProwessAPL

STORMCHASER    = "Stormchaser's Talent"
THUNDERTRAP    = "Thundertrap Trainer"
SPLASH_PORTAL  = "Splash Portal"
BOOMERANG      = "Boomerang Basics"
QUANTUM        = "Quantum Riddler"
TORCH          = "Torch the Tower"
GET_OUT        = "Get Out"
FROSTCLIFF     = "Frostcliff Siege"
RAL            = "Ral, Crackling Wit"
STOCK_UP       = "Stock Up"

ANNUL          = "Annul"
FLASHFREEZE    = "Flashfreeze"
ILL_TIMED      = "Ill-Timed Explosion"
FLOOD_MAW      = "Into the Flood Maw"
DISDAINFUL     = "Disdainful Stroke"
NEGATE         = "Negate"
ABRADE         = "Abrade"
WAN_SHI_TONG   = "Wan Shi Tong, Librarian"


class IzzetBlinkStandardMatchAPL(AwareMatchAPL, IzzetProwessAPL):
    name = "Izzet Blink"
    ARCHETYPE = "tempo"

    # Hold {U} for Boomerang Basics / Splash Portal responses
    COUNTER_COST  = 1
    COUNTER_CARDS = {ANNUL, FLASHFREEZE, DISDAINFUL, NEGATE}

    MATCH_REMOVAL = {
        TORCH:   ("R",  3),     # 3 damage instant
        GET_OUT: ("1R", None),  # exile any size, instant
    }
    MATCH_EXILE = {GET_OUT, FLOOD_MAW}

    SB_PLANS = {
        "aggro": (
            # vs Red/Aggro: removal + Flashfreeze
            [FLASHFREEZE, FLASHFREEZE, ABRADE, ILL_TIMED, ILL_TIMED],
            [SPLASH_PORTAL, SPLASH_PORTAL, BOOMERANG, RAL, STOCK_UP],
        ),
        "control": (
            # vs Control: Negate + Disdainful; keep drawing with blink value
            [NEGATE, DISDAINFUL, RAL, WAN_SHI_TONG, ABRADE],
            [TORCH, TORCH, TORCH, BOOMERANG, SPLASH_PORTAL],
        ),
        "combo": (
            # vs Izzet Lessons: Annul Monument/Talent; flood maw bounces
            [ANNUL, ANNUL, NEGATE, FLOOD_MAW, FLOOD_MAW, WAN_SHI_TONG],
            [SPLASH_PORTAL, SPLASH_PORTAL, BOOMERANG, RAL, STOCK_UP, FROSTCLIFF],
        ),
        "ramp": (
            # vs Rhythm: Annul Nature's Rhythm; Disdainful Stroke for big ETBs
            [ANNUL, ANNUL, FLASHFREEZE, FLASHFREEZE, DISDAINFUL],
            [SPLASH_PORTAL, BOOMERANG, RAL, TORCH, STOCK_UP],
        ),
        "tempo": (
            # vs mirror: Abrade for creatures; Ill-Timed Explosion sweep
            [ABRADE, ILL_TIMED, ILL_TIMED, FLASHFREEZE, FLASHFREEZE],
            [BOOMERANG, BOOMERANG, SPLASH_PORTAL, RAL, STOCK_UP],
        ),
    }
