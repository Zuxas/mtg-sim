"""apl/izzet_lesson_standard_match.py -- Izzet Lesson match APL.

Multi-inherits MatchAPL + IzzetLessonAPL so the goldfish turn loop
(ControlAPL with categorized disruption) runs unchanged in match
mode. MatchAPL provides declare_attackers / declare_blockers /
respond_to_spell hooks with sensible defaults.

Gran-Gran mechanics (SOS, added 2026-05-01):
  Static cost reduction wired in IzzetLessonAPL.main_phase().
  Loot tap trigger wired in declare_attackers below.
"""
from data.card import Tag
from apl.match_apl import MatchAPL
from apl.izzet_lesson import IzzetLessonAPL, GRAN_GRAN
from engine.match_state import safe_power, safe_toughness


class IzzetLessonStandardMatchAPL(MatchAPL, IzzetLessonAPL):
    ARCHETYPE = "control"
    SB_PLANS = {
        "aggro": (
            ["1 Abrade", "1 Pyroclasm", "1 Slagstorm", "1 Iroh's Demonstration"],
            ["3 Abandon Attachments", "1 Starting Town"],
        ),
        "control": (
            ["2 Annul", "1 Flashfreeze", "1 Negate", "1 Spell Pierce",
             "1 Abhorrent Oculus"],
            ["4 Combustion Technique", "2 It'll Quench Ya!"],
        ),
        "combo": (
            ["3 Soul-Guide Lantern", "2 Annul", "1 Negate", "1 Spell Pierce"],
            ["4 Combustion Technique", "2 It'll Quench Ya!", "1 Agna Qel'a"],
        ),
        "ramp": (
            ["1 Flashfreeze", "1 Negate", "1 Spell Pierce", "2 Quantum Riddler"],
            ["4 Combustion Technique", "1 It'll Quench Ya!"],
        ),
        "tempo": (
            ["1 Abrade", "1 Pyroclasm", "1 Slagstorm", "2 Annul"],
            ["3 Abandon Attachments", "2 It'll Quench Ya!"],
        ),
    }

    def declare_attackers(self, gs, opponent):
        """Attack with everything non-summoning-sick.

        Gran-Gran tap trigger: 'Whenever Gran-Gran becomes tapped, draw
        a card, then discard a card.' Oracle (SOS, verified).
        Proxy: fires on attack (most common tap), once per turn.
        """
        attackers = [c for c in gs.zones.battlefield
                     if not c.is_land() and c.has(Tag.CREATURE)
                     and not getattr(c, 'summoning_sickness', False)
                     and not getattr(c, 'tapped', False)]

        # Gran-Gran loot on tap (attacks -> becomes tapped)
        for c in attackers:
            if c.name == GRAN_GRAN:
                gs.zones.draw(1)
                if gs.zones.hand:
                    worst = min(gs.zones.hand,
                                key=lambda x: (0 if x.is_land() else
                                               getattr(x, 'cmc', 0)))
                    gs.zones.hand.remove(worst)
                    gs.zones.graveyard.append(worst)
                    gs._log(f"  Gran-Gran loot (tap trigger): draw 1, "
                            f"discard {worst.name}")

        return attackers

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers:
            return assignments
        blockers = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()
                    and not getattr(c, 'tapped', False)
                    and safe_toughness(c) >= 2]
        if blockers:
            biggest = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest) >= 2:
                assignments[id(biggest)] = [blockers[0]]
        return assignments
