"""apl/izzet_spellementals_standard.py -- Izzet Spellementals (Standard)

U/R control-tempo deck built around Elementals that scale with
graveyard count. Fill the graveyard with Opt / Sleight / Winternight
Stories, then cast Hearth Elemental / Eddymurk Crab / Sunderflock for
drastically reduced mana.

Engine caveat: the 'this spell costs X less' mechanic isn't modeled
yet; we cast the Elementals at their printed cost. The deck still
wins via Sunderflock's 5/5 flying body + the 11 cantrips + counters
keeping things stable, but turn-counts are slower than real play.

Composes ControlAPL — this deck is more control than prowess (5
counters, 11 cantrips, 12 creature threats spread across the top).
"""
from apl.control_base import ControlAPL

# ── Reactive ────────────────────────────────────────────────────────
SPELL_PIERCE  = "Spell Pierce"        # {U}: counter noncreature unless 2
SPELL_SNARE   = "Spell Snare"         # {U}: counter 2-cmc spell
ABRADE        = "Abrade"              # {1}{R}: 3 dmg or destroy artifact
SEAR          = "Sear"                # {1}{R}: 4 dmg to creature/PW

# ── Hand attack (treat as proactive; goldfish no target) ───────────
ABANDON       = "Abandon Attachments"
BOUNCE        = "Bounce Off"

# ── Cheap burn ──────────────────────────────────────────────────────
BURST         = "Burst Lightning"

# ── Elemental finishers (big-cmc + draw) ───────────────────────────
HEARTH        = "Hearth Elemental"    # 6-cmc 4/5 (GY-scaling cost)
EDDY          = "Eddymurk Crab"       # 7-cmc 5/5 flash (GY-scaling cost)
SUNDER        = "Sunderflock"         # 9-cmc 5/5 flying (Elemental-scaling)

# ── Cantrips / draw ────────────────────────────────────────────────
OPT           = "Opt"
SLEIGHT       = "Sleight of Hand"
WINTERNIGHT   = "Winternight Stories"
DRAGONHUNT    = "Glacial Dragonhunt"


class IzzetSpellementalsAPL(ControlAPL):
    name = "Izzet Spellementals"
    max_turns = 14

    # Hand attack fires proactively on curve
    HAND_ATTACK = (ABANDON, BOUNCE)

    # Reactive interaction — held up through main 1
    REMOVAL = (
        SPELL_PIERCE,   # {U}
        SPELL_SNARE,    # {U}
        ABRADE,         # {1}{R}
        SEAR,           # {1}{R}
    )

    # Counters we'd never tap out of — but since Spell Pierce and
    # Spell Snare are also typed as REMOVAL here, they're reserved.
    COUNTERS = (SPELL_PIERCE, SPELL_SNARE)

    # No mainboard wipes
    WIPES = ()

    # Elemental threats, cheapest-first (printed cost)
    THREATS = (
        HEARTH,     # 6-cmc 4/5
        EDDY,       # 7-cmc 5/5 flash
        SUNDER,     # 9-cmc 5/5 flying, bounces non-Elementals
    )

    VALUE_SPELLS = (
        OPT,             # {U}
        SLEIGHT,         # {U}
        WINTERNIGHT,     # {2}{U}
        DRAGONHUNT,      # {U}{R} draw + discard → damage
        BURST,           # {R}: 2 dmg face
    )

    # 20 lands, wants 4+ to start deploying Elementals. Aggressive
    # mulligan range.
    MULL_MIN_LANDS = 2
    MULL_MAX_LANDS = 5
