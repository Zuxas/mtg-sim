"""apl/azorius_aggro_standard.py -- Azorius Merfolk Aggro (Standard)

Current #5 Standard archetype (~9.5% meta). Merfolk tribal tempo
with flash creatures + untap-after-attack shenanigans.

Play pattern: land, 1-drop Wanderbrine Trapper, T2 Silvergill Mentor
(ETB makes a 1/1 Merfolk token), T3 Disruptor of Currents (flash
bounce), swing in, chain more flash creatures on opp turns.

Engine caveats:
  * Deepchannel Duelist's +1/+1 lord effect not modeled; the 2/2
    just attacks as printed.
  * Sygg's Command Spree modes (copy Merfolk / draw card) not wired;
    the spell resolves without effect other than prowess trigger.
  * Convoke on Disruptor of Currents ignored; cast at printed
    {3}{U}{U}.

Still posts reasonable aggro numbers because creature density is high
and the cheap 2-drops snowball attacks.
"""
from apl.aggro_base import AggroAPL

# ── 1-drops ──────────────────────────────────────────────────────────
WANDERBRINE  = "Wanderbrine Trapper"      # {W} 2/1

# ── 2-drops ──────────────────────────────────────────────────────────
DEEPCHANNEL  = "Deepchannel Duelist"      # {W}{U} 2/2, Lord for Merfolk
DEEPWAY      = "Deepway Navigator"        # {W}{U} 2/2 flash
SILVERGILL   = "Silvergill Mentor"        # {1}{U} 2/1, ETB token
FLOODPITS    = "Floodpits Drowner"        # {1}{U} 2/1 flash
MINDSPRING   = "Mindspring Merfolk"       # {U} 1/1, exhaust draw

# ── 3-drops ──────────────────────────────────────────────────────────
TIDEBINDER   = "Tishana's Tidebinder"     # {2}{U} 3/2 flash, counter ability

# ── 5-drops ──────────────────────────────────────────────────────────
DISRUPTOR    = "Disruptor of Currents"    # {3}{U}{U} 3/3 flash bounce

# ── Spells ──────────────────────────────────────────────────────────
SYGGS_CMD    = "Sygg's Command"           # {1}{W}{U} Spree modes
THREE_STEPS  = "Three Steps Ahead"        # {U} Spree counter/draw


class AzoriusAggroAPL(AggroAPL):
    name = "Azorius Aggro"
    max_turns = 11

    CREATURES = (
        MINDSPRING,     # 1-drop
        WANDERBRINE,    # 1-drop
        DEEPCHANNEL,    # 2-drop (Lord + attacker)
        DEEPWAY,        # 2-drop flash
        SILVERGILL,     # 2-drop, ETB token
        FLOODPITS,      # 2-drop flash
        TIDEBINDER,     # 3-drop flash
        DISRUPTOR,      # 5-drop flash bounce
    )

    CANTRIP_SPELLS = (
        SYGGS_CMD,      # Spree — cast for prowess even without target
        THREE_STEPS,    # Spree
    )

    # No direct burn in mainboard
    BURN_SPELLS = {}

    # No pump
    PUMP_SPELLS = {}

    HASTE_CREATURES = frozenset()

    # Aggro mulligan — lots of 2-cost creatures, 2-3 lands is fine
    MULL_MIN_LANDS = 2
    MULL_MAX_LANDS = 4
