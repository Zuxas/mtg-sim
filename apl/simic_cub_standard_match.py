"""
apl/simic_cub_standard_match.py — Simic Cub / Badgermole (Standard)

whitehatman 2026-02-22 1st place list. Landfall-ramp-combo shell.

Plan:
  T1  Llanowar Elves (mana dork)
  T2  Badgermole Cub (landfall +1/+1 grower) — bolstered by further
      land drops every turn via Multiversal Passage / fetch-style
      Willowrush Verge triggers.
  T3  Gene Pollinator or Quantum Riddler (ETB value creatures)
  T4  Nature's Rhythm (tutors for a creature and ramps a land)
  T5+ Craterhoof Behemoth or Ouroboroid (finisher)

Since the engine already models landfall via on_landfall in card_effects,
Badgermole Cub will naturally grow as lands drop. This APL just
sequences the creature deployment + Nature's Rhythm tutoring.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness


BADGERMOLE_CUB    = "Badgermole Cub"
LLANOWAR_ELVES    = "Llanowar Elves"
GENE_POLLINATOR   = "Gene Pollinator"
QUANTUM_RIDDLER   = "Quantum Riddler"
SPIDER_MANIFEST   = "Spider Manifestation"
MOCKINGBIRD       = "Mockingbird"
KEEN_EYED         = "Keen-Eyed Curator"
SURRAK            = "Surrak, Elusive Hunter"
WISTFULNESS       = "Wistfulness"
OUROBOROID        = "Ouroboroid"
CRATERHOOF        = "Craterhoof Behemoth"
NATURES_RHYTHM    = "Nature's Rhythm"
ARCHDRUIDS_CHARM  = "Archdruid's Charm"
SPIDER_SENSE      = "Spider-Sense"


RAMP = {LLANOWAR_ELVES}
LANDFALL_CORE = {BADGERMOLE_CUB}
# Deploy order for threats — earliest to latest
THREAT_ORDER = (
    LLANOWAR_ELVES,
    BADGERMOLE_CUB,
    KEEN_EYED,
    GENE_POLLINATOR,
    MOCKINGBIRD,
    QUANTUM_RIDDLER,
    SURRAK,
    SPIDER_MANIFEST,
    OUROBOROID,
    CRATERHOOF,
)


class SimicCubStandardMatchAPL(MatchAPL):
    ARCHETYPE = "ramp"
    name = "Simic Cub (Badgermole)"
    win_condition_damage = 20
    max_turns = 12

    SB_PLANS = {
        "aggro": (
            ["2 Unable to Scream", "1 Soul-Guide Lantern",
             "2 Shimmerwilds Growth", "1 Keen-Eyed Curator"],
            ["1 Craterhoof Behemoth", "2 Archdruid's Charm",
             "2 Spider-Sense", "1 Surrak, Elusive Hunter"],
        ),
        "control": (
            ["2 Disdainful Stroke", "1 Champion of the Weird",
             "1 Oko, Lorwyn Liege"],
            ["2 Keen-Eyed Curator", "1 Wistfulness",
             "1 Spider-Sense"],
        ),
        "combo": (
            ["1 Soul-Guide Lantern", "2 Disdainful Stroke",
             "1 Into the Flood Maw"],
            ["2 Mockingbird", "1 Surrak, Elusive Hunter",
             "1 Craterhoof Behemoth"],
        ),
        "ramp": (
            ["2 Disdainful Stroke", "1 Ygra, Eater of All",
             "1 Into the Flood Maw"],
            ["2 Keen-Eyed Curator", "2 Mockingbird"],
        ),
        "tempo": (
            ["2 Unable to Scream", "1 Into the Flood Maw",
             "2 Shimmerwilds Growth"],
            ["2 Archdruid's Charm", "2 Spider-Sense",
             "1 Wistfulness"],
        ),
    }

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        ramp = sum(1 for c in hand if c.name == LLANOWAR_ELVES)
        creatures = sum(1 for c in hand if c.has(Tag.CREATURE))
        if lands < 2 or lands > 5:
            return False
        if ramp >= 1 and creatures >= 2:
            return True
        if lands >= 3 and creatures >= 2:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                         key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[3:] + spells)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """Ramp + landfall-grower + finisher tutor."""
        self._play_land_if_able(gs)
        gs.tap_lands()

        # 1. T1 Llanowar Elves first — ramp enables turn-3 4-drops
        for c in list(gs.zones.hand):
            if c.name == LLANOWAR_ELVES and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 2. Nature's Rhythm — tutor value. Goldfish approx: cast it,
        # the spell effect doesn't resolve fully (no targeting), but
        # it counts toward prowess-style board presence.
        for c in list(gs.zones.hand):
            if c.name == NATURES_RHYTHM and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 3. Creatures in priority order — Badgermole Cub first so it
        # soaks the most landfall triggers.
        for name in THREAT_ORDER:
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # 4. Archdruid's Charm as mid-game flex value
        for c in list(gs.zones.hand):
            if c.name == ARCHDRUIDS_CHARM and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 5. Remaining creatures / spells
        for c in list(gs.zones.hand):
            if gs.mana_pool.can_cast(c.mana_cost, c.cmc) and c.has(Tag.CREATURE):
                gs.cast_spell(c)

    def declare_attackers(self, gs, opponent):
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land():
                continue
            if getattr(c, 'summoning_sickness', False):
                continue
            if getattr(c, 'tapped', False):
                continue
            if not c.has(Tag.CREATURE):
                continue
            # Llanowar Elves stays back as mana source
            if c.name == LLANOWAR_ELVES:
                continue
            attackers.append(c)
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers:
            return assignments
        blockers = [c for c in gs.zones.battlefield
                     if c.has(Tag.CREATURE) and not c.is_land()
                     and not getattr(c, 'tapped', False)
                     and c.name != LLANOWAR_ELVES]
        if not blockers:
            return assignments
        # Badgermole Cub with counters can block big attackers
        cubs = sorted([b for b in blockers if b.name == BADGERMOLE_CUB],
                       key=lambda c: -safe_toughness(c))
        biggest_att = max(attackers, key=lambda c: safe_power(c))
        if cubs and safe_toughness(cubs[0]) >= safe_power(biggest_att):
            assignments[id(biggest_att)] = [cubs[0]]
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        """Prefer basics / Forest / untapped duals; fetches later for
        extra landfall triggers via Multiversal Passage."""
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        def score(c):
            n = (c.name or '').lower()
            if 'passage' in n:
                return 0  # fetch first — extra landfall
            if 'forest' in n or 'pool' in n or 'sanctum' in n:
                return 1
            if 'willowrush' in n:
                return 2
            return 3
        gs.play_land(min(lands, key=score))
