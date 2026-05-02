"""apl/izzet_prowess_standard.py -- Izzet Prowess APL (Standard)

PT Secrets of Strixhaven build (2026-05-01). 30.5% of PT field (99/325).
U/R aggro-burn hybrid built around prowess creatures + cheap cantrips.

SOS additions (added 2026-05-01):
  Flow State      — impulse-style cantrip, draws 2 with instant+sorcery in GY
  Colorstorm Stallion — 3/3 haste, Opus (+1/+1 per instant/sorcery cast)
  Prismari Charm  — modal: surveil+draw / 1 damage / bounce
  Traumatic Critique — {X}{U}{R}: X damage + draw 2/discard 1
  Impractical Joke — {R}: 3 unpreventable damage to creature/player

Play pattern:
  T1: Elusive Otter (1/1 prowess) or cantrip
  T2: Slickshot Show-Off (haste prowess) + Flow State to fill GY
  T2-3: Chain Flow State/cantrips pre-combat → prowess pump → attack
  T3+: Colorstorm Stallion as 3/3 haste; each cantrip = +1/+1 Opus pump
"""
from apl.aggro_base import AggroAPL

# ── 1-drops ──────────────────────────────────────────────────────────
ELUSIVE_OTTER  = "Elusive Otter"          # 1/1 prowess (not in oracle DB yet)
HEARTH_ELEM    = "Hearth Elemental"        # not in oracle DB yet

# ── 2-drops ──────────────────────────────────────────────────────────
SLICKSHOT      = "Slickshot Show-Off"
STORMCHASER    = "Stormchaser's Talent"   # Class — makes 1/1 Otter

# ── SOS 3-drop ───────────────────────────────────────────────────────
COLORSTORM     = "Colorstorm Stallion"    # {1}{U}{R} 3/3 haste, Opus trigger

# ── Top end ──────────────────────────────────────────────────────────
EDDYMURK       = "Eddymurk Crab"

# ── Cantrips / draw ──────────────────────────────────────────────────
OPT            = "Opt"
SLEIGHT        = "Sleight of Hand"
STOCK_UP       = "Stock Up"
BOUNCE         = "Bounce Off"
BOOMERANG      = "Boomerang Basics"
FLOW_STATE     = "Flow State"             # {1}{U} impulse: top 3, take 1 (or 2 with IS+SS in GY)
PRISMARI_CHARM = "Prismari Charm"         # {U}{R} modal: surveil+draw / 1 dmg / bounce

# ── Burn ────────────────────────────────────────────────────────────
BURST          = "Burst Lightning"        # {R}: 2 dmg, kicker for 4
IMPRACTICAL    = "Impractical Joke"       # {R}: 3 unpreventable dmg to creature/player
TRAUMATIC      = "Traumatic Critique"     # {X}{U}{R}: X dmg + draw 2/discard 1

# ── Pump ────────────────────────────────────────────────────────────
WILD_RIDE      = "Wild Ride"             # {R}: +3/+0 haste


class IzzetProwessAPL(AggroAPL):
    name = "Izzet Prowess"
    max_turns = 10

    CREATURES = (
        ELUSIVE_OTTER,   # 1-drop prowess
        SLICKSHOT,       # 2-drop flying haste + prowess
        STORMCHASER,     # 2-drop Class, makes Otter token
        COLORSTORM,      # 3-drop haste, Opus (prowess-like per spell)
        EDDYMURK,        # top-end 7-drop with cost reduction
    )

    CANTRIP_SPELLS = (
        OPT,             # {U}: scry 1, draw 1
        SLEIGHT,         # {U}: draw 1
        FLOW_STATE,      # {1}{U}: impulse top 3 (draws 2 with IS+SS in GY) — key SOS add
        PRISMARI_CHARM,  # {U}{R}: modal — surveil+draw mode used here
        STOCK_UP,        # {2}{U}: draw 2
        BOUNCE,          # {U}: bounce — prowess trigger
        BOOMERANG,       # {1}{U}: bounce
    )

    BURN_SPELLS = {
        BURST:          (1, 2),   # {R}: 2 dmg to face
        IMPRACTICAL:    (1, 3),   # {R}: 3 unpreventable dmg (kill 3-toughness or face)
        TRAUMATIC:      (3, 3),   # {X}{U}{R}: flexible burn, draw 2/discard 1
    }

    PUMP_SPELLS = {
        WILD_RIDE: (1, 3, False),  # {R}: +3/+0 haste
    }

    HASTE_CREATURES = frozenset({SLICKSHOT, COLORSTORM})

    # Aggressive: 2 lands with lots of cantrips is playable
    MULL_MIN_LANDS = 2
    MULL_MAX_LANDS = 4
