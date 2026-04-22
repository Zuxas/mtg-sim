"""apl/izzet_prowess_standard.py -- Izzet Prowess APL (Standard)

Current #1 Standard archetype (Apr 2026). U/R aggro-burn hybrid built
around prowess creatures (Monastery Swiftspear-alikes) + lots of cheap
cantrips + direct damage.

Play pattern:
  T1: Elusive Otter (1/1 prowess) or cantrip
  T2: Slickshot Show-Off (1/2 flying haste, prowess) — attacks T2
  T2-3: Cast cantrips pre-combat, Stormchaser's Talent for Otter token
  T3+: Curve into Stock Up (draw 2), keep chaining cantrips → prowess
        pump → burn face → attack

Composes AggroAPL with the new CANTRIP_SPELLS slot. Opt / Sleight of
Hand / Stock Up / Bounce Off all cast pre-combat to pump prowess and
draw more gas.
"""
from apl.aggro_base import AggroAPL

# ── 1-drops ──────────────────────────────────────────────────────────
ELUSIVE_OTTER  = "Elusive Otter"

# ── 2-drops ──────────────────────────────────────────────────────────
SLICKSHOT      = "Slickshot Show-Off"
STORMCHASER    = "Stormchaser's Talent"      # Class — makes 1/1 Otter

# ── Top end (flash blocker / finisher) ──────────────────────────────
EDDYMURK       = "Eddymurk Crab"

# ── Cantrips ─────────────────────────────────────────────────────────
OPT            = "Opt"
SLEIGHT        = "Sleight of Hand"
STOCK_UP       = "Stock Up"
BOUNCE         = "Bounce Off"
BOOMERANG      = "Boomerang Basics"

# ── Burn ────────────────────────────────────────────────────────────
BURST          = "Burst Lightning"           # {R}: 2 dmg, kicker for 4

# ── Pump ────────────────────────────────────────────────────────────
WILD_RIDE      = "Wild Ride"                 # {R}: +3/+0 haste


class IzzetProwessAPL(AggroAPL):
    name = "Izzet Prowess"
    max_turns = 10

    CREATURES = (
        ELUSIVE_OTTER,   # 1-drop prowess
        SLICKSHOT,       # 2-drop flying haste + prowess
        STORMCHASER,     # 2-drop Class, makes Otter token ETB
        EDDYMURK,        # top-end 7-drop with cost reduction
    )

    CANTRIP_SPELLS = (
        OPT,             # {U}: draw 1 (+ scry)
        SLEIGHT,         # {U}: draw 1
        STOCK_UP,        # {2}{U}: draw 2
        BOUNCE,          # {U}: bounce — prowess trigger
        BOOMERANG,       # {1}{U}: bounce
    )

    BURN_SPELLS = {
        BURST: (1, 2),   # {R}: 2 dmg to face
    }

    PUMP_SPELLS = {
        WILD_RIDE: (1, 3, False),   # {R}: +3/+0 haste (we skip haste flag)
    }

    HASTE_CREATURES = frozenset({SLICKSHOT})

    # Aggressive: 2 lands with lots of cantrips is playable
    MULL_MIN_LANDS = 2
    MULL_MAX_LANDS = 4
