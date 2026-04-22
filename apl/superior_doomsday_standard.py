"""apl/superior_doomsday_standard.py -- Superior Doomsday APL (Standard)

#2 current Standard archetype (15.5% meta). Despite the name, this
isn't a Doomsday combo deck — it's a Dimir control deck that wins
with Doomsday Excruciator (6/6 flying demon for {BBBBBB}). Superior
Spider-Man and Harvester of Misery round out the threat suite.

Play pattern (real Magic):
  T1-T3: Interaction. Cut Down / Bitter Triumph / Requiting Hex
         on opp threats. Stock Up for card flow.
  T4-T5: Deadly Cover-Up wipe if threatened. Spider-Man if a big
         creature is available to copy.
  T6+:   Cast Doomsday Excruciator. 6/6 flying takes 4 turns to kill.

Composes ControlAPL. No combo — just draw, answer, stick the
flying fatty.
"""
from apl.control_base import ControlAPL

# ── Proactive / hand attack ──────────────────────────────────────────
INTIMIDATION = "Intimidation Tactics"     # {B} sorcery, target discard

# ── Reactive removal ─────────────────────────────────────────────────
BITTER       = "Bitter Triumph"           # {1}{B}: exile creature/PW
REQUITING    = "Requiting Hex"            # {B}: kill 2-or-less cmc creature

# ── Wipes ────────────────────────────────────────────────────────────
COVER_UP     = "Deadly Cover-Up"          # {3}{B}{B}: wipe

# ── Threats (cheapest-first, ControlAPL casts biggest affordable) ───
DECEIT       = "Deceit"                   # {4}{U/B}{U/B}: ETB bounce or discard
HARVESTER    = "Harvester of Misery"      # {3}{B}{B}: ETB -2/-2 wipe, 5/4
SPIDER_MAN   = "Superior Spider-Man"      # {2}{U}{B}: copy GY creature as 4/4
EXCRUCIATOR  = "Doomsday Excruciator"     # {BBBBBB}: 6/6 flying finisher
MALBORO      = "Malboro"                  # {4}{B}{B}: discard+drain trigger

# ── Value / setup ───────────────────────────────────────────────────
STOCK_UP     = "Stock Up"                 # {2}{U}: draw 2
WINTERNIGHT  = "Winternight Stories"      # {2}{U}: draw 3, discard 2
AVARICE      = "Insatiable Avarice"       # {B}: tutor / draw
CHARM        = "Archenemy's Charm"        # {B}{B}{B}: utility
QUANTUM      = "Quantum Riddler"          # utility


class SuperiorDoomsdayAPL(ControlAPL):
    name = "Superior Doomsday"
    max_turns = 14

    HAND_ATTACK = (INTIMIDATION,)

    REMOVAL = (
        REQUITING,   # {B}: kills 2-or-less cmc
        BITTER,      # {1}{B}: exile anything
    )

    COUNTERS = ()

    WIPES = (COVER_UP,)

    THREATS = (
        SPIDER_MAN,    # {2}{U}{B} — 4-cmc 4/4, GY copy
        DECEIT,        # {4}{U/B}{U/B} — 6-cmc 5/5 elemental
        HARVESTER,     # {3}{B}{B} — 5-cmc 5/4 with ETB wipe
        MALBORO,       # {4}{B}{B} — 6-cmc 4/4 discard trigger
        EXCRUCIATOR,   # {BBBBBB} — 6-cmc 6/6 flying, THE WIN CON
    )

    VALUE_SPELLS = (
        AVARICE,       # {B} spree
        STOCK_UP,
        WINTERNIGHT,
        CHARM,
    )

    # Dimir / mono-black: 22 lands, wants 3+ for T3 Cover Up/Requiting,
    # 6 for Excruciator on T6
    MULL_MIN_LANDS = 2
    MULL_MAX_LANDS = 6
