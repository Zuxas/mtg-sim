"""apl/izzet_prowess_nick_tokyo_standard.py -- Nick Odenheimer Tokyo build (2026-05-10)

Worldly Counsel post-PT-SOS / RC Tokyo update. Diff vs PT consensus:
  REMOVED: Elusive Otter, Wild Ride, Three Steps Ahead, Colorstorm Stallion, Stock Up
  ADDED:   2 Prismari Charm main, Roaring Furnace // Steaming Sauna, Get Out, Wan Shi Tong (SB), Ral (SB)

Source: Team Resolve/worldly_council_prowess_guide.md
Decklist: decks/izzet_prowess_nick_tokyo_standard.txt

Goldfish gameplan:
  T1: Spirebluff Canal -> Opt / Sleight (NOT a threat-first deck; cantrip dig)
  T2: Stormchaser's Talent OR plot Slickshot Show-Off OR cantrip
  T3: Slickshot from plot OR Boomerang Talent for prowess + 1/1 Otter trigger
  T4-5: Eddymurk Crab (cost-reduced by I/S in GY; flash-drop opp end step)
  T5-6: Roaring Furnace (cards-in-hand removal) or open Steaming Sauna for value
"""
from apl.izzet_prowess_standard import IzzetProwessAPL


# ── Card name constants for Nick's Tokyo build ──────────────────────
SLICKSHOT      = "Slickshot Show-Off"
STORMCHASER    = "Stormchaser's Talent"
EDDYMURK       = "Eddymurk Crab"

OPT            = "Opt"
SLEIGHT        = "Sleight of Hand"
BOOMERANG      = "Boomerang Basics"
FLOW_STATE     = "Flow State"
PRISMARI_CHARM = "Prismari Charm"

BURST          = "Burst Lightning"
IMPRACTICAL    = "Impractical Joke"

GET_OUT        = "Get Out"
SPELL_PIERCE   = "Spell Pierce"
FURNACE        = "Roaring Furnace // Steaming Sauna"


class IzzetProwessNickTokyoAPL(IzzetProwessAPL):
    """Nick's Tokyo Prowess: cantrip-heavy, no 1-drop creature, plot-and-burst plan."""

    name = "Izzet Prowess (Nick Tokyo)"
    max_turns = 10

    # Tokyo build has NO 1-drop creature (no Elusive Otter / Hearth Elemental).
    # Stormchaser's Talent is a Class enchantment, but we keep it here so the
    # deploy logic in AggroAPL.main_phase can recognize it as a primary play.
    CREATURES = (
        SLICKSHOT,    # 2-drop {1}{R} flying haste +2/+0 per noncreature spell
        STORMCHASER,  # 2-drop {U} Class -- Otter token + Lv2/Lv3 paths
        EDDYMURK,     # top-end {5}{U}{U} -- 4/4 flash, cost-reduced by I/S in GY
    )

    CANTRIP_SPELLS = (
        OPT,             # {U}: scry 1, draw 1
        SLEIGHT,         # {U}: scry 2, draw 1
        FLOW_STATE,      # {1}{U}: impulse top 3
        PRISMARI_CHARM,  # {U}{R}: modal -- surveil+draw / 1 dmg / bounce. 2 main in Tokyo.
        BOOMERANG,       # {1}{U}: bounce -- triggers prowess + Stormchaser Lv1 Otter
    )

    # Tokyo SB removes Wild Ride (no pump spells).
    PUMP_SPELLS = {}

    BURN_SPELLS = {
        BURST:        (1, 2),   # {R}: 2 dmg face (kicker for 4 -- key Ral combo enabler)
        IMPRACTICAL:  (1, 3),   # {R}: 3 unpreventable dmg to creature/player. 1 main.
    }

    # Slickshot has haste from PLOT cast; Stormchaser doesn't attack (it's an enchantment).
    HASTE_CREATURES = frozenset({SLICKSHOT})

    # Tokyo mulligan thresholds per Nick's primer:
    #  - On the draw, double-cantrip 1-lander = 95% snap keep
    #  - Mirror requires cantrip-heavy hands (no-cantrip mull)
    # We allow slightly wider land range than typical aggro since cantrips dig hard.
    MULL_MIN_LANDS = 1   # one-landers OK with double cantrip
    MULL_MAX_LANDS = 5
