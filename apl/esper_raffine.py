"""apl/esper_raffine.py -- Esper Raffine APL (Standard)

Disruption-heavy midrange anchored by Raffine + Liliana. Composes
ControlAPL with the new categorized disruption: Liliana is a
proactive edict (casts on curve), Cut Down/Throat/Anoint are held as
reactive mana (cast post-combat), Cover Up is a wipe.

Play pattern:
  T1-T2: land, deploy Faerie Mastermind (flash it up post-combat)
  T3: Raffine (ward {1}) + hold Cut Down mana open
  T4: Liliana proactive edict; if no Liliana, Jace for mill pressure
  T5+: Archfiend / Loch Whale beats + removal answers on demand
"""
from apl.control_base import ControlAPL

# ── Proactive — cast on curve ───────────────────────────────────────
LILIANA      = "Liliana of the Veil"      # {1}{B}{B}: edict + loyalty

# ── Reactive removal — held up through main phase 1 ────────────────
CUT_DOWN     = "Cut Down"                 # {B}: kill small
THROAT       = "Go for the Throat"        # {1}{B}: kill non-artifact
ANOINT       = "Anoint with Affliction"   # {2}{B}: destroy + mill

# ── Wipe ─────────────────────────────────────────────────────────────
COVER_UP     = "Deadly Cover-Up"          # {3}{B}{B}: wipe

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


class EsperRaffineAPL(ControlAPL):
    name = "Esper Raffine"
    max_turns = 14

    # Liliana is proactive — +1 ability is an edict on cast-turn
    HAND_ATTACK = (LILIANA,)

    # Point removal — hold mana open through main phase 1
    REMOVAL = (
        CUT_DOWN,     # {B}
        THROAT,       # {1}{B}
        ANOINT,       # {2}{B}
    )

    # Wipe — only cast when the board demands it (goldfish default:
    # never; subclass could override _should_wipe for match play)
    WIPES = (COVER_UP,)

    # No counters in the mainboard list
    COUNTERS = ()

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
