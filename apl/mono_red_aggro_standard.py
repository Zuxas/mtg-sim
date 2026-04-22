"""apl/mono_red_aggro_standard.py -- Mono Red Aggro APL (Standard)

Pure red creature + burn deck. Hired Claw haste pressure, Emberheart
Challenger card advantage, Lightning Strike / Burst Lightning reach,
Nova Hellkite as a top-end finisher.

Distinct from apl/mono_red_aggro.py which is Modern Burn. Analyzer
picks this up via the _standard filename suffix.
"""
from apl.aggro_base import AggroAPL

# ── 1-drops ──────────────────────────────────────────────────────────
HIRED_CLAW   = "Hired Claw"            # 1/1 haste

# ── 2-drops ──────────────────────────────────────────────────────────
BURNOUT      = "Burnout Bashtronaut"
EMBERHEART   = "Emberheart Challenger"
RAZORKIN     = "Razorkin Needlehead"

# ── 3-drop ──────────────────────────────────────────────────────────
SCREAMING    = "Screaming Nemesis"

# ── Top-end ─────────────────────────────────────────────────────────
NOVA         = "Nova Hellkite"

# ── Burn ────────────────────────────────────────────────────────────
SHOCK        = "Shock"
BURST        = "Burst Lightning"
LIGHTNING    = "Lightning Strike"
OBLITERATE   = "Obliterating Bolt"
FRENZY       = "Witchstalker Frenzy"


class MonoRedAggroStandardAPL(AggroAPL):
    name = "Mono Red Aggro"
    max_turns = 10

    CREATURES = (
        HIRED_CLAW,                                # 1-drop
        EMBERHEART, BURNOUT, RAZORKIN,             # 2-drops
        SCREAMING,                                 # 3-drop
        NOVA,                                      # top-end
    )

    BURN_SPELLS = {
        SHOCK:      (1, 2),     # {R}: 2 dmg
        BURST:      (1, 2),     # {R}: 2 dmg (can kicker later for 4)
        LIGHTNING:  (2, 3),     # {1}{R}: 3 dmg
        OBLITERATE: (3, 4),     # {2}{R}: 4 dmg
    }

    PUMP_SPELLS = {}            # Pure burn — no pump spells

    HASTE_CREATURES = frozenset({HIRED_CLAW})

    # Aggressive mulligan — 1-landers still viable if hand is loaded
    MULL_MIN_LANDS = 1
    MULL_MAX_LANDS = 3
