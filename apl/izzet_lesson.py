"""apl/izzet_lesson.py -- Izzet Lesson APL (Standard)

Tempo/control shell with Saga 'Lesson' cards and cheap damage spells.
Updated to Zhang Rui's PT SOS #1-seed list (2026-05-01).
49.44% overall PT WR; 75% vs Selesnya Landfall; loses to Mono-Green 41.9%.

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

# ── SOS additions (Zhang Rui PT list 2026-05-01) ────────────────────
CONSULT      = "Consult the Star Charts"  # 2-cmc scry+draw
THREE_STEPS  = "Three Steps Ahead"        # 3-cmc copy/counter
AGNA         = "Agna Qel'a"               # 2-cmc value creature
SPELL_PIERCE = "Spell Pierce"             # 1-cmc soft counter

# ── Big spells (threats) ────────────────────────────────────────────
IROH         = "Iroh's Demonstration"     # finisher
QUENCH       = "It'll Quench Ya!"         # big spell


class IzzetLessonAPL(ControlAPL):
    name = "Izzet Lesson"
    max_turns = 14

    # No hand attack in this archetype
    HAND_ATTACK = ()

    # Burn doubles as removal AND face damage — don't hold it all game.
    # In fair matchups these clear the path; in goldfish they go face.
    # Listed cheapest first so mana reservation stays minimal.
    REMOVAL = (
        COMBUSTION,       # {1}{R} 2 damage — burns creatures or face
        ABANDON,          # {1}{R} artifact/ench hate
        BOOMERANG,        # {1}{U} bounce tempo
    )

    # Three Steps Ahead acts as soft counter in match; model as counter
    COUNTERS = (
        THREE_STEPS,      # {1}{U}{U} copy/counter — held for opp threats
        SPELL_PIERCE,     # {U} soft counter
    )

    # No mainboard wipes
    WIPES = ()

    # Threats — Sagas/Classes tick up for value + pressure.
    # Order cheapest first; biggest-castable chosen each turn.
    THREATS = (
        GRAN_GRAN,        # 1-drop creature
        AGNA,             # 2-drop value creature
        FIREBENDING,      # 2-cmc Saga, deals damage per chapter
        ARTIST,           # 2-cmc Class, draw engine
        MONUMENT,         # 3-cmc recur engine
        QUENCH,           # 4-cmc finisher
        IROH,             # 5-cmc finisher
    )

    # Card-advantage engines (cast freely — no mana reservation for these)
    VALUE_SPELLS = (
        CONSULT,          # scry 2 + draw 1 — cast pre-combat for selection
        ACCUMULATE,       # draw 2
    )

    # Izzet mulligans looser — 2 colors, 20 mana sources, no 1-drops needed
    MULL_MIN_LANDS = 2
    MULL_MAX_LANDS = 5

    # ------------------------------------------------------------------
    # Gran-Gran static + loot (SOS, 2026-05-01)
    # ------------------------------------------------------------------

    def _lesson_count_in_gy(self, gs):
        """Count Lesson cards in our graveyard (for Gran-Gran thresholds)."""
        return sum(1 for c in gs.zones.graveyard
                   if 'Lesson' in (getattr(c, 'type_line', '') or '')
                   or c.name in (FIREBENDING, STORMCHASER, ARTIST))

    def main_phase(self, gs):
        """Override to apply Gran-Gran static before any spell casting.

        Oracle (Gran-Gran, SOS, verified):
          'Noncreature spells you cast cost {1} less to cast as long as
           there are three or more Lesson cards in your graveyard.'
        Proxy: set mana_pool.cost_reduction = 1 at turn start when
        Gran-Gran is on board and threshold is met. Resets naturally
        in mana_pool.empty() at next turn boundary.
        """
        gran_on_board = any(c.name == GRAN_GRAN for c in gs.zones.battlefield
                            if not c.is_land())
        if gran_on_board and self._lesson_count_in_gy(gs) >= 3:
            gs.mana_pool.cost_reduction = max(gs.mana_pool.cost_reduction, 1)
            gs._log("  Gran-Gran static: noncreature spells cost {1} less "
                    "(3+ Lessons in GY)")
        super().main_phase(gs)

    # ------------------------------------------------------------------
    # Match-mode: fire burn aggressively when behind on the damage race
    # ------------------------------------------------------------------

    def main_phase2(self, gs):
        """Post-combat: prioritize burn when opp has a threatening board.

        In fair matchups this deck wins by racing — Firebending Lesson
        chapters + burn to face. When we're losing the damage race
        (opp has 3+ power on board), cast all available burn immediately
        rather than holding for reactive mana.
        """
        opp = getattr(self, "_opp_gs", None)
        opp_power = 0
        if opp is not None:
            from data.card import Tag
            for c in opp.zones.battlefield:
                if c.has(Tag.CREATURE):
                    try:
                        opp_power += int(c.power or 0)
                    except (ValueError, TypeError):
                        opp_power += 2
        # If opp has 3+ power threatening us, burn aggressively (don't hold)
        # This models casting Combustion Technique at opp's best creature
        # to slow the clock, then going face with the rest.
        if opp_power >= 3:
            self._cast_in_priority(gs, self.REMOVAL)
        super().main_phase2(gs)

    # ------------------------------------------------------------------
    # Archetype hooks — level up Classes when mana permits
    # ------------------------------------------------------------------

    def _custom_precombat(self, gs):
        """After threats are deployed, pour leftover mana into Class
        level-ups. Priority: Stormchaser's Talent Level 3 (token per
        instant/sorcery = scaling pressure). Artist's Talent Level 3
        (noncombat damage +2) is less relevant in goldfish since we
        rarely deal noncombat damage through spells."""
        from engine.classes import level_up, CLASS_DEFS
        for perm in list(gs.zones.battlefield):
            if perm.name not in CLASS_DEFS:
                continue
            # Try leveling up until mana runs out. The level_up call
            # handles the cost check and returns False when can't
            # advance further, breaking the while.
            while level_up(perm, gs):
                pass
