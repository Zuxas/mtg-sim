"""
apl/azorius_omniscience_standard_match.py — Azorius Omniscience (Standard)

Token-doubling Elspeth + Cosmogrand Zenith engine. Elspeth doubles all
token creation; Cosmogrand makes tokens on 2nd spell each turn; Serra
Paragon recurs valuable permanents from GY. Mangara draws against aggro.

Win condition: token flood with doubled Elspeth → large attack.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness
from apl.card_specs import (multi_set_standard, edge_of_eternities,
                              serra_paragon as sp, strixhaven_support)

ELSPETH_ST   = "Elspeth, Storm Slayer"
VOICE_VIC    = "Voice of Victory"
COSMOGRAND   = edge_of_eternities.COSMOGRAND_ZENITH
MANGARA      = strixhaven_support.MANGARA
NOVICE_INSP  = multi_set_standard.NOVICE_INSPECTOR
ENDURING_INN = "Enduring Innocence"
HONOR        = "Honor"
GET_LOST     = "Get Lost"
SERRA_PAR    = sp.NAME

THREATS = {ELSPETH_ST, COSMOGRAND, VOICE_VIC, NOVICE_INSP, SERRA_PAR, MANGARA}


class AzoriusOmniscienceMatchAPL(MatchAPL):
    name = "Azorius Omniscience"
    win_condition_damage = 20
    max_turns = 14

    def __init__(self):
        self._spells_this_turn = 0

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in THREATS)
        if lands == 0: return False
        if lands >= 3 and threats >= 1: return True
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
        self._play_land_if_able(gs)
        gs.tap_lands()
        self._spells_this_turn = 0
        elspeth_active = any(c.name == ELSPETH_ST for c in gs.zones.battlefield)

        # T1: Novice Inspector (Clue + draw engine)
        for c in list(gs.zones.hand):
            if c.name == NOVICE_INSP and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                self._spells_this_turn += 1
                multi_set_standard._on_resolve(gs, NOVICE_INSP, c, opponent)
                break

        # T2: Voice of Victory (mobilize 2)
        for c in list(gs.zones.hand):
            if c.name == VOICE_VIC and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                self._spells_this_turn += 1
                break

        # T3: Elspeth, Storm Slayer (token doubler)
        for c in list(gs.zones.hand):
            if c.name == ELSPETH_ST and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                self._spells_this_turn += 1
                gs._log(f"  Elspeth Storm Slayer: all tokens created are doubled!")
                break

        # T3: Mangara anti-aggro draw
        for c in list(gs.zones.hand):
            if c.name == MANGARA and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                self._spells_this_turn += 1
                strixhaven_support._on_resolve(gs, MANGARA, c, opponent)
                break

        # T4: Cosmogrand Zenith (2nd spell = 2 tokens × 2 with Elspeth = 4)
        for c in list(gs.zones.hand):
            if c.name == COSMOGRAND and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                self._spells_this_turn += 1
                n_tokens = 4 if elspeth_active else 2
                if self._spells_this_turn >= 2:
                    for _ in range(n_tokens):
                        tok = Card("Soldier Token", "{0}", 1, "Token Creature — Soldier")
                        tok.power = "1"; tok.toughness = "1"
                        tok.turn_entered = gs.turn; tok.summoning_sickness = True
                        gs.zones.battlefield.append(tok)
                    gs._log(f"  Cosmogrand: {n_tokens} tokens (Elspeth: {'×2' if elspeth_active else '×1'})")
                break

        # Serra Paragon: recur best CMC<=3 from GY
        for c in list(gs.zones.hand):
            if c.name == SERRA_PAR and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                self._spells_this_turn += 1
                break
        sp.use_recursion(gs, opponent)
        sp.reset_turn_flag(gs)

        # Removal
        if opponent:
            threats = [x for x in opponent.zones.battlefield if not x.is_land()]
            if threats:
                for c in list(gs.zones.hand):
                    if c.name == GET_LOST and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        gs.cast_spell(c)
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
        gs.play_land(lands[0])
