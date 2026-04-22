"""apl/izzet_lesson.py -- Izzet Lesson APL (Standard)

Tempo/control shell with Saga 'Lesson' cards and cheap damage spells.
Top Standard archetype at 23% meta share (Jan 2026).

Play pattern (real Magic):

  Lesson Sagas (Firebending Lesson, Stormchaser's Talent, Artist's
  Talent) are multi-chapter enchantments — T2 deploy, they tick up
  each turn to deal damage, draw a card, and eventually sac for
  payoff. They're treated as 'threats' that also supply value.

  Gran-Gran is a 1-drop creature. Stormchaser's Talent drops 1/1
  elemental tokens along the way.

  Cheap removal (Combustion Technique, Abandon Attachments,
  Boomerang Basics) — categorized as REMOVAL, held up through main
  phase 1 to answer opp threats.

  Monument to Endurance — land-like value engine, treated as a
  value spell since it doesn't answer anything.

  Iroh's Demonstration, It'll Quench Ya! — big finisher spells,
  threats near the top end.

Composes ControlAPL with the new categorized-disruption split.
"""
from apl.control_base import ControlAPL

# ── Creatures ───────────────────────────────────────────────────────
GRAN_GRAN    = "Gran-Gran"                # 1-drop
QUANTUM      = "Quantum Riddler"          # sideboard

# ── Lesson Sagas / Classes (threats + value) ────────────────────────
FIREBENDING  = "Firebending Lesson"       # Saga, damage chapters
STORMCHASER  = "Stormchaser's Talent"     # Class, scales up
ARTIST       = "Artist's Talent"          # Class, copy/draw

# ── Cantrips / value ────────────────────────────────────────────────
ACCUMULATE   = "Accumulate Wisdom"        # draw
MONUMENT     = "Monument to Endurance"    # recur engine

# ── Removal ─────────────────────────────────────────────────────────
COMBUSTION   = "Combustion Technique"     # cheap damage/removal
ABANDON      = "Abandon Attachments"      # artifact/enchantment hate
BOOMERANG    = "Boomerang Basics"         # bounce

# ── Big spells (threats) ────────────────────────────────────────────
IROH         = "Iroh's Demonstration"     # finisher
QUENCH       = "It'll Quench Ya!"         # big spell


class IzzetLessonAPL(ControlAPL):
    name = "Izzet Lesson"
    max_turns = 14

    # No hand attack in this archetype (blue-red doesn't run Thoughtseize)
    HAND_ATTACK = ()

    # Reactive removal — hold mana open through main 1
    REMOVAL = (
        COMBUSTION,       # {1}{R} damage
        ABANDON,          # {1}{R} artifact/ench hate
        BOOMERANG,        # {1}{U} bounce
    )

    # No hardcoded counters in mainboard; sideboard-only (Annul / Negate)
    COUNTERS = ()

    # No mainboard wipes
    WIPES = ()

    # Threats — Sagas tick up for value while pressuring life total.
    # Order cheapest first; ControlAPL casts biggest-castable per turn.
    THREATS = (
        GRAN_GRAN,        # 1-drop creature
        FIREBENDING,      # 2-cmc Saga
        STORMCHASER,      # 2-cmc Class
        ARTIST,           # 2-cmc Class
        MONUMENT,         # 3-cmc engine
        QUENCH,           # 4-cmc big spell
        IROH,             # 5-cmc finisher
    )

    # Card-advantage engines
    VALUE_SPELLS = (
        ACCUMULATE,       # draw 2
    )

    # Izzet mulligans looser than esper — 2 colors, 20 mana sources
    MULL_MIN_LANDS = 2
    MULL_MAX_LANDS = 5
