# Auto-generated match APL for Simic Rhythm (standard)
# Generated: 2026-04-19 by gemma_apl_chunked.py
# Role: midrange | Max turns: 10 | Blocking: favorable
#
# Gemma analyzed 10 cards, produced 8 priority rules

from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

BADGERMOLE_CUB = "Badgermole Cub"
GENE_POLLINATOR = "Gene Pollinator"
LLANOWAR_ELVES = "Llanowar Elves"
NATURES_RHYTHM = "Nature's Rhythm"
OUROBOROID = "Ouroboroid"
QUANTUM_RIDDLER = "Quantum Riddler"


class SimicRhythmStandardMatchAPL(MatchAPL):
    name = "Simic Rhythm"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        creatures = sum(1 for c in hand if c.has(Tag.CREATURE))
        spells = len(hand) - lands - creatures
        if lands < 1: return False
        if lands > 5: return False
        if creatures >= 1 and lands >= 2: return True
        if creatures + spells >= 3 and lands >= 2: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, "cmc", 0))
        return (lands[3:] + spells)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()

        # Llanowar Elves
        for c in list(gs.zones.hand):
            if c.name == "Llanowar Elves" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Nature's Rhythm (utility)
        for c in list(gs.zones.hand):
            if c.name == "Nature's Rhythm" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Badgermole Cub
        for c in list(gs.zones.hand):
            if c.name == "Badgermole Cub" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Gene Pollinator
        for c in list(gs.zones.hand):
            if c.name == "Gene Pollinator" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Ouroboroid
        for c in list(gs.zones.hand):
            if c.name == "Ouroboroid" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Quantum Riddler
        for c in list(gs.zones.hand):
            if c.name == "Quantum Riddler" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Llanowar Elves
        for c in list(gs.zones.hand):
            if c.name == "Llanowar Elves" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Nature's
        for c in list(gs.zones.hand):
            if c.name == "Nature's" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break


        # Cast any remaining creatures
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield
                if c.has(Tag.CREATURE) and not c.is_land()
                and not getattr(c, "summoning_sickness", False)
                and not getattr(c, "tapped", False)]

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)
                    and not c.is_land() and not getattr(c, "tapped", False)
                    and safe_power(c) >= 3]
        if blockers and attackers:
            biggest_att = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest_att) >= 3:
                best_blocker = max(blockers, key=lambda c: safe_toughness(c))
                assignments[id(biggest_att)] = [best_blocker]
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        gs.play_land(lands[0])
