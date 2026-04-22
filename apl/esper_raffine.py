"""apl/esper_raffine.py -- Esper Raffine APL (Standard)

Disruption-heavy midrange anchored by Raffine + Liliana. Wins via
value creatures (Faerie Mastermind, Raffine) swinging while removal
clears the way.

Composes ControlAPL. No archetype-specific hooks needed — the value
engine is just 'cast spells'.
"""
from apl.control_base import ControlAPL

# ── Disruption ──────────────────────────────────────────────────────
CUT_DOWN     = "Cut Down"                 # {B}: kill small
THROAT       = "Go for the Throat"        # {1}{B}: kill non-artifact
ANOINT       = "Anoint with Affliction"   # {2}{B}: destroy + mill
LILIANA      = "Liliana of the Veil"      # {1}{B}{B}: edict + loyalty

# ── Threats ─────────────────────────────────────────────────────────
FAERIE       = "Faerie Mastermind"        # {1}{U}: flash flier
RAFFINE      = "Raffine, Scheming Seer"   # {W}{U}{B}: ward, connive
LOCH_WHALE   = "Horned Loch-Whale"        # {4}{U}: ward, big flier
JACE         = "Jace, the Perfected Mind" # {2}{U}: mill PW
ARCHFIEND    = "Archfiend of the Dross"   # {3}{B}{B}: oil threat
EXCRUCIATOR  = "Doomsday Excruciator"     # {5}{B}{B}: huge beater

# ── Value / setup ───────────────────────────────────────────────────
CRYPTIC_COAT = "Cryptic Coat"             # {1}{U}: manifest
NEGOTIATION  = "Binding Negotiation"      # sorcery treasure/draw
COVER_UP     = "Deadly Cover-Up"          # {3}{B}{B}: wipe


class EsperRaffineAPL(ControlAPL):
    name = "Esper Raffine"
    max_turns = 14

    DISRUPTION = (
        CUT_DOWN,     # {B}
        THROAT,       # {1}{B}
        ANOINT,       # {2}{B}
        LILIANA,      # {1}{B}{B}
        COVER_UP,     # {3}{B}{B}: wipe
    )

    THREATS = (
        FAERIE,       # {1}{U}
        RAFFINE,      # {W}{U}{B}
        JACE,         # {2}{U}
        LOCH_WHALE,   # {4}{U}
        ARCHFIEND,    # {3}{B}{B}
        EXCRUCIATOR,  # {5}{B}{B}
    )

    VALUE_SPELLS = (
        CRYPTIC_COAT,
        NEGOTIATION,
    )

    # 3-color deck — mulligan for fixing + 2 relevant cards
    MULL_MIN_LANDS = 2
    MULL_MAX_LANDS = 5
