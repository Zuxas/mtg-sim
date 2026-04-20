# Auto-generated match APL for Jeskai Control (standard)
# Generated: 2026-04-19 by gemma_apl_chunked.py
# Role: midrange | Max turns: 10 | Blocking: favorable
#
# Gemma analyzed 17 cards, produced 9 priority rules

from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

CONSULT_THE_STAR_CHARTS = "Consult the Star Charts"
GET_LOST = "Get Lost"
INEVITABLE_DEFEAT = "Inevitable Defeat"
LIGHTNING_HELIX = "Lightning Helix"
NO_MORE_LIES = "No More Lies"
JESKAI_REVELATION = "Jeskai Revelation"
DAY_OF_JUDGMENT = "Day of Judgment"
STOCK_UP = "Stock Up"
THREE_STEPS_AHEAD = "Three Steps Ahead"
ULTIMA = "Ultima"


class JeskaiControlStandardMatchAPL(MatchAPL):
    name = "Jeskai Control"
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

        # Get Lost (removal)
        if opponent:
            for c in list(gs.zones.hand):
                if c.name == "Get Lost" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    opp_cr = [x for x in opponent.zones.battlefield
                              if not x.is_land() and x.has(Tag.CREATURE)]
                    if opp_cr:
                        t = max(opp_cr, key=lambda x: safe_power(x))
                        gs.mana_pool.pay(c.mana_cost, c.cmc)
                        gs.zones.hand.remove(c)
                        gs.zones.graveyard.append(c)
                        opponent.zones.battlefield.remove(t)
                        opponent.zones.graveyard.append(t)
                        gs._log("  Get Lost: kill " + t.name)
                    break

        # No More Lies (removal)
        if opponent:
            for c in list(gs.zones.hand):
                if c.name == "No More Lies" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    opp_cr = [x for x in opponent.zones.battlefield
                              if not x.is_land() and x.has(Tag.CREATURE)]
                    if opp_cr:
                        t = max(opp_cr, key=lambda x: safe_power(x))
                        gs.mana_pool.pay(c.mana_cost, c.cmc)
                        gs.zones.hand.remove(c)
                        gs.zones.graveyard.append(c)
                        opponent.zones.battlefield.remove(t)
                        opponent.zones.graveyard.append(t)
                        gs._log("  No More Lies: kill " + t.name)
                    break

        # Inevitable Defeat (removal)
        if opponent:
            for c in list(gs.zones.hand):
                if c.name == "Inevitable Defeat" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    opp_cr = [x for x in opponent.zones.battlefield
                              if not x.is_land() and x.has(Tag.CREATURE)]
                    if opp_cr:
                        t = max(opp_cr, key=lambda x: safe_power(x))
                        gs.mana_pool.pay(c.mana_cost, c.cmc)
                        gs.zones.hand.remove(c)
                        gs.zones.graveyard.append(c)
                        opponent.zones.battlefield.remove(t)
                        opponent.zones.graveyard.append(t)
                        gs._log("  Inevitable Defeat: kill " + t.name)
                    break

        # Day of Judgment (removal)
        if opponent:
            for c in list(gs.zones.hand):
                if c.name == "Day of Judgment" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    opp_cr = [x for x in opponent.zones.battlefield
                              if not x.is_land() and x.has(Tag.CREATURE)]
                    if opp_cr:
                        t = max(opp_cr, key=lambda x: safe_power(x))
                        gs.mana_pool.pay(c.mana_cost, c.cmc)
                        gs.zones.hand.remove(c)
                        gs.zones.graveyard.append(c)
                        opponent.zones.battlefield.remove(t)
                        opponent.zones.graveyard.append(t)
                        gs._log("  Day of Judgment: kill " + t.name)
                    break

        # Jeskai Revelation (utility)
        for c in list(gs.zones.hand):
            if c.name == "Jeskai Revelation" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Stock Up (utility)
        for c in list(gs.zones.hand):
            if c.name == "Stock Up" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Consult the Star Charts (utility)
        for c in list(gs.zones.hand):
            if c.name == "Consult the Star Charts" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Three Steps Ahead (utility)
        for c in list(gs.zones.hand):
            if c.name == "Three Steps Ahead" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 
        for c in list(gs.zones.hand):
            if c.name == "" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
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
