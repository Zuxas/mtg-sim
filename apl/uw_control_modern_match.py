"""
apl/uw_control_modern_match.py -- UW Control (Modern), R1 priority-stack opt-in

This is the REAL control APL that opts into the R1 on-stack LIFO priority loop
(design 1.5, "control subclass only" scope). It subclasses AwareMatchAPL and
sets WANTS_PRIORITY_STACK = True, so the engine routes casts through
engine.priority_stack.run_priority_stack -- letting this deck counter on the
stack (and counter the counter) using the inherited priority_action /
_r1_choose_counter heuristics, which themselves lift COUNTER_VALIDITY /
_spell_value / _PRIORITY_COUNTER_TARGETS from engine.counter_resolver.

The base AwareMatchAPL keeps WANTS_PRIORITY_STACK = False, so the other 37
Standard match decks stay on the bit-identical legacy gate-OFF path. Only this
class flips the gate on.

Decklist: decks/uw_control_modern.txt (chosen over jeskai_control_modern.txt
for the cleaner, denser mono-color counter suite:
  2 Counterspell {U}{U}, 2 Spell Snare {U}, 1 Force of Negation {1}{U}{U},
  1 Subtlety (free counter for creature/PW spells)).

Gameplan (classic draw-go control):
  - Counterspell priority: protect our own engine, answer opp threats/engines on
    the stack via the shared COUNTER_VALIDITY heuristics. Hold up counter mana.
  - Removal: Solitude (evoke exile), Prismatic Ending (exile any small nonland
    permanent), March of Otherworldly Light (exile artifact/creature/enchant).
  - Board wipes: Supreme Verdict / Wrath of the Skies vs a developed board.
  - Card advantage / win-late: Narset, Teferi, Jace, The Wandering Emperor,
    Wan Shi Tong, Stock Up -- deployed by the goldfish fallback once threats are
    answered and counter mana is no longer needed.
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from engine.match_state import safe_power, safe_toughness
from apl.aware_match_apl import AwareMatchAPL
from apl.uw_control import UWControlAPL

# ---- Card names (exact oracle spellings; mirror decks/uw_control_modern.txt) ----
SOLITUDE        = "Solitude"
SUBTLETY        = "Subtlety"
PRISMATIC_END   = "Prismatic Ending"
MARCH_LIGHT     = "March of Otherworldly Light"
SUPREME_VERDICT = "Supreme Verdict"
WRATH_SKIES     = "Wrath of the Skies"
COUNTERSPELL    = "Counterspell"
SPELL_SNARE     = "Spell Snare"
FORCE_NEGATION  = "Force of Negation"
MYSTICAL_DISP   = "Mystical Dispute"
CONSIGN_MEMORY  = "Consign to Memory"
WANDERING_EMP   = "The Wandering Emperor"

# Hard/soft counters this deck actually runs (drives reserve_mana + attack
# holdback). All of these are recognized by engine.counter_resolver.COUNTER_VALIDITY,
# so the inherited R1 priority_action will pick them up on the stack automatically.
COUNTERSPELLS = {COUNTERSPELL, SPELL_SNARE, FORCE_NEGATION, SUBTLETY,
                 MYSTICAL_DISP, CONSIGN_MEMORY}

# Board wipes -- handled explicitly (NOT in MATCH_REMOVAL, which is spot-removal
# dispatch). Mirrors the Jeskai control APL's Day of Judgment handling.
WIPES = {SUPREME_VERDICT, WRATH_SKIES}

# Creatures/permanents to answer on sight with exile-quality removal.
KILL_PRIORITY = (
    "Ragavan, Nimble Pilferer",     # snowballs Treasure/exile; answer early
    "Scion of Draco",
    "Phlage, Titan of Fire's Fury", # recursive engine
    "Sheoldred, the Apocalypse",
    "Murktide Regent",
    "Kaito, Bane of Nightmares",
)


class UWControlModernMatchAPL(AwareMatchAPL, UWControlAPL):
    """UW Control (Modern). Opts into the R1 priority stack."""

    name = "UW Control"
    ARCHETYPE = "control"

    # R1 OPT-IN: this is the one class in the tree that flips the gate on.
    WANTS_PRIORITY_STACK = True

    # Hold up counter mana (Counterspell / Force of Negation == 2-ish).
    COUNTER_COST  = 2
    COUNTER_CARDS = COUNTERSPELLS

    # Spot removal dispatch table: name -> (doc_cost, max_toughness_gate).
    # The first element is documentation only (engine pays from card.mana_cost);
    # max_toughness None means "answers anything" (these are exile effects).
    MATCH_REMOVAL = {
        SOLITUDE:      ("evoke / 1WW", None),   # exile target creature
        PRISMATIC_END: ("X / WU pips", None),   # exile nonland permanent MV<=X
        MARCH_LIGHT:   ("XW", None),            # exile artifact/creature/enchant
    }
    # All our spot removal exiles -> prefer it for blink/recursion-resistant kills.
    MATCH_EXILE = {SOLITUDE, PRISMATIC_END, MARCH_LIGHT}

    # ------------------------------------------------------------------
    # Never tap out: always represent counter / removal mana.
    # ------------------------------------------------------------------
    def reserve_mana(self, gs: GameState, opponent: GameState):
        has_counter = any(c.name in self.COUNTER_CARDS for c in gs.zones.hand)
        has_removal = any(c.name in self.MATCH_REMOVAL for c in gs.zones.hand)
        if has_counter:
            gs.mana_reserve = self.COUNTER_COST
        elif has_removal:
            gs.mana_reserve = 2
        else:
            gs.mana_reserve = 0

    # ------------------------------------------------------------------
    # Main phase: wipe -> kill-priority -> spot removal -> deploy card advantage.
    # ------------------------------------------------------------------
    def main_phase_match(self, gs: GameState, opponent: GameState):
        self._play_land_if_able(gs)
        if hasattr(self, "reserve_mana"):
            self.reserve_mana(gs, opponent)
        gs.tap_lands()
        self._opp_gs = opponent

        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]

        # Board wipe when the opponent has developed a real board (3+ creatures).
        if len(opp_creatures) >= 3:
            for c in list(gs.zones.hand):
                if c.name in WIPES and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.noncreature_spells_this_turn += 1
                    for victim in list(opp_creatures):
                        if victim in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(victim)
                            opponent.zones.graveyard.append(victim)
                    gs._log(f"  {c.name}: wiped {len(opp_creatures)} creatures")
                    return

        # Answer kill-priority threats with exile-quality removal first.
        for name in KILL_PRIORITY:
            target = next((c for c in opp_creatures if c.name == name), None)
            if target and self._kill_with_removal(gs, opponent, target,
                                                  prefer_exile=True):
                return

        # Otherwise spot-remove the single biggest threat.
        if opp_creatures:
            target = max(opp_creatures, key=lambda c: safe_power(c))
            self._kill_with_removal(gs, opponent, target, prefer_exile=True)

        # Deploy card-advantage / planeswalkers / win-late pieces with whatever
        # mana is left (the goldfish fallback handles the planeswalker pile).
        self._cast_all_castable(gs)

    # ------------------------------------------------------------------
    # Pre-combat: exile kill-priority attackers before they connect.
    # ------------------------------------------------------------------
    def pre_combat_instant(self, gs: GameState, opponent: GameState):
        opp_creatures = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land()]
        for name in KILL_PRIORITY:
            for c in opp_creatures:
                if c.name == name and self._kill_with_removal(
                        gs, opponent, c, prefer_exile=True):
                    gs._log(f"  [pre-combat] exiled {c.name}")
                    return
        super().pre_combat_instant(gs, opponent)

    # ------------------------------------------------------------------
    # Blocking: control deck soaks the biggest attackers with its toughest bodies.
    # ------------------------------------------------------------------
    def declare_blockers(self, gs: GameState, opponent: GameState, attackers: list):
        if not attackers:
            return {}
        my_creatures = [c for c in gs.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()
                        and not getattr(c, 'summoning_sickness', False)
                        and not getattr(c, 'tapped', False)]
        assignments = {}
        used = set()
        for atk in sorted(attackers, key=lambda c: -safe_power(c)):
            blk = next((b for b in sorted(my_creatures,
                                          key=lambda c: -safe_toughness(c))
                        if id(b) not in used), None)
            if blk is None:
                break
            assignments[id(atk)] = [blk]
            used.add(id(blk))
        return assignments
