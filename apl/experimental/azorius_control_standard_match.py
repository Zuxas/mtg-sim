# Auto-generated match APL for Azorius Control (standard)
# Generated: 2026-04-19 by gemma_apl_chunked.py
# Role: control | Max turns: 15 | Blocking: favorable
#
# Gemma analyzed 6 cards, produced 14 priority rules

from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

COSMOGRAND_ZENITH = "Cosmogrand Zenith"
ENDURING_INNOCENCE = "Enduring Innocence"
NOVICE_INSPECTOR = "Novice Inspector"
SEAM_RIP = "Seam Rip"
VOICE_OF_VICTORY = "Voice of Victory"


class AzoriusControlStandardMatchAPL(MatchAPL):
    name = "Azorius Control"
    win_condition_damage = 20
    max_turns = 15

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

        # Seam Rip (removal)
        if opponent:
            for c in list(gs.zones.hand):
                if c.name == "Seam Rip" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    opp_cr = [x for x in opponent.zones.battlefield
                              if not x.is_land() and x.has(Tag.CREATURE)]
                    if opp_cr:
                        t = max(opp_cr, key=lambda x: safe_power(x))
                        gs.mana_pool.pay(c.mana_cost, c.cmc)
                        gs.zones.hand.remove(c)
                        gs.zones.graveyard.append(c)
                        opponent.zones.battlefield.remove(t)
                        opponent.zones.graveyard.append(t)
                        gs._log("  Seam Rip: kill " + t.name)
                    break

        # Novice Inspector
        for c in list(gs.zones.hand):
            if c.name == "Novice Inspector" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Enduring Innocence (enchantment)
        for c in list(gs.zones.hand):
            if c.name == "Enduring Innocence" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Voice of Victory (pump)
        for c in list(gs.zones.hand):
            if c.name == "Voice of Victory" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Cosmogrand Zenith (utility)
        for c in list(gs.zones.hand):
            if c.name == "Cosmogrand Zenith" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Placeholder
        for c in list(gs.zones.hand):
            if c.name == "Placeholder" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Placeholder
        for c in list(gs.zones.hand):
            if c.name == "Placeholder" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Placeholder
        for c in list(gs.zones.hand):
            if c.name == "Placeholder" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Placeholder
        for c in list(gs.zones.hand):
            if c.name == "Placeholder" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Placeholder
        for c in list(gs.zones.hand):
            if c.name == "Placeholder" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Placeholder
        for c in list(gs.zones.hand):
            if c.name == "Placeholder" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Placeholder
        for c in list(gs.zones.hand):
            if c.name == "Placeholder" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Placeholder
        for c in list(gs.zones.hand):
            if c.name == "Placeholder" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Placeholder
        for c in list(gs.zones.hand):
            if c.name == "Placeholder" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
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
