"""
apl/azorius_control_standard_match.py — Azorius Control (Standard, August 2025)

Token-swarm control. Win with Novice Inspector Clues + Voice of Victory
Warriors + Cosmogrand Zenith tokens. Remove threats with Get Lost + Seam Rip.
Enduring Innocence draws on every small ETB creature.

Replaced old version (blue-heavy control) with current white-primary token build.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness
from apl.card_specs import multi_set_standard, edge_of_eternities

COSMOGRAND   = "Cosmogrand Zenith"
ENDURING_INN = "Enduring Innocence"
NOVICE_INSP  = "Novice Inspector"
SEAM_RIP     = "Seam Rip"
VOICE_VIC    = "Voice of Victory"
ELSPETH_ST   = "Elspeth, Storm Slayer"
GET_LOST     = "Get Lost"
STARFIELD    = "Starfield Shepherd"
NURTURING    = "Nurturing Pixie"

THREATS = {ENDURING_INN, VOICE_VIC, NOVICE_INSP, STARFIELD}


class AzoriusControlMatchAPL(MatchAPL):
    name = "Azorius Control"
    win_condition_damage = 20
    max_turns = 14

    def __init__(self):
        self._spells_cast_this_turn = 0

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in THREATS)
        if lands == 0: return False
        if lands >= 3 and threats >= 1: return True
        if lands >= 2 and threats >= 2: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        excess = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        to_bottom = excess[4:]
        filler = [c for c in hand if not c.is_land() and c not in to_bottom
                  and c.name not in THREATS]
        return (to_bottom + filler)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        if opponent is not None:
            gs._match_opp = opponent
        self._play_land_if_able(gs)
        gs.tap_lands()
        self._spells_cast_this_turn = 0

        # 1. Novice Inspector T1
        for c in list(gs.zones.hand):
            if c.name == NOVICE_INSP and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                self._spells_cast_this_turn += 1
                multi_set_standard._on_resolve(gs, NOVICE_INSP, c, opponent)
                break

        # 2. Voice of Victory T2
        for c in list(gs.zones.hand):
            if c.name == VOICE_VIC and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                self._spells_cast_this_turn += 1
                break

        # 3. Enduring Innocence T3
        for c in list(gs.zones.hand):
            if c.name == ENDURING_INN and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                self._spells_cast_this_turn += 1
                if self._spells_cast_this_turn >= 2:
                    gs.zones.draw(1)
                break

        # 4. Cosmogrand Zenith — 2nd spell = two 1/1 tokens
        for c in list(gs.zones.hand):
            if c.name == COSMOGRAND and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                self._spells_cast_this_turn += 1
                if self._spells_cast_this_turn >= 2:
                    for _ in range(2):
                        tok = Card("Soldier Token", "{0}", 1, "Token Creature — Soldier")
                        tok.power = "1"; tok.toughness = "1"
                        tok.turn_entered = gs.turn; tok.summoning_sickness = True
                        gs.zones.battlefield.append(tok)
                    gs._log(f"  Cosmogrand Zenith: 2 Soldier tokens")
                break

        # 5. Elspeth Storm Slayer
        for c in list(gs.zones.hand):
            if c.name == ELSPETH_ST and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                self._spells_cast_this_turn += 1
                break

        # 6. Removal
        if opponent:
            for removal_name in (SEAM_RIP, GET_LOST):
                threats = [x for x in opponent.zones.battlefield if not x.is_land()]
                if threats:
                    for c in list(gs.zones.hand):
                        if c.name == removal_name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                            gs.cast_spell(c)
                            if removal_name == SEAM_RIP:
                                edge_of_eternities._on_resolve(gs, SEAM_RIP, c, opponent)
                            else:
                                multi_set_standard._on_resolve(gs, GET_LOST, c, opponent)
                            break

        self._cast_all_castable(gs)

    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield
                if c.has(Tag.CREATURE) and not c.is_land()
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()
                    and not getattr(c, 'tapped', False)
                    and not getattr(c, 'summoning_sickness', False)]
        if blockers:
            biggest = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest) >= 3:
                assignments[id(biggest)] = [max(blockers, key=lambda c: safe_toughness(c))]
        return assignments

    def respond_to_spell(self, gs, opponent, spell): return None
    def end_step_actions(self, gs, opponent): pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if 'plains' in n: return 1
            return 2
        gs.play_land(min(lands, key=score))
