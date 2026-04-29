"""
apl/simic_ouroboroid_standard_match.py — Simic Ouroboroid (Standard)

Counter-scaling engine. Ouroboroid distributes counters to ALL creatures
at combat. With Ozolith (+1 extra per counter placed) and Nev (trample for
countered creatures), generates an unstoppable trampling board.

Game plan:
T2: Ozolith + Gene Pollinator (mana dork)
T3: Nev the Practical Dean (trample for countered creatures)
T4: Ouroboroid (begin-combat: put X counters on each, where X = Ouro's counters)
T5+: Zimone Infinite Analyst (X-spell discount), Mightform Harmonizer (double power)
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness
from apl.card_specs import (edge_of_eternities, strixhaven_support)
from engine.keywords import KWTag

OUROBOROID   = edge_of_eternities.OUROBOROID
OZOLITH      = "Ozolith, the Shattered Spire"
NEV          = strixhaven_support.NEV
ZIMONE       = strixhaven_support.ZIMONE_ANALYST
ICETILL      = edge_of_eternities.ICETILL_EXPLORER
MIGHTFORM    = edge_of_eternities.MIGHTFORM_HARMONIZER
GENE_POLL    = edge_of_eternities.GENE_POLLINATOR
STRIDING     = strixhaven_support.STRIDING
CONSULT      = edge_of_eternities.CONSULT_STAR_CHARTS

ENGINE = {OUROBOROID, OZOLITH, NEV, ZIMONE}


class SimicOuroboroidMatchAPL(MatchAPL):
    name = "Simic Ouroboroid"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        has_engine = any(c.name in ENGINE for c in hand)
        if lands == 0: return False
        if has_engine and lands >= 2: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        excess = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        to_bottom = excess[3:]
        filler = [c for c in hand if not c.is_land() and c not in to_bottom
                  and c.name not in ENGINE]
        return (to_bottom + filler)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()

        # T2: Ozolith (all counters placed +1)
        for c in list(gs.zones.hand):
            if c.name == OZOLITH and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Ozolith: +1 counter amplifier active")
                break

        # T2: Gene Pollinator (mana dork)
        for c in list(gs.zones.hand):
            if c.name == GENE_POLL and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # T3: Nev (trample for countered creatures)
        for c in list(gs.zones.hand):
            if c.name == NEV and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                strixhaven_support._on_resolve(gs, NEV, c, opponent)
                break

        # T4: Ouroboroid (the engine)
        for c in list(gs.zones.hand):
            if c.name == OUROBOROID and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Ouroboroid: begin-combat distributes counters to all")
                break

        # Combat trigger: Ouroboroid distributes X counters
        edge_of_eternities.ouroboroid_combat_trigger(gs)
        # Apply trample to all countered creatures
        strixhaven_support.nev_apply_trample(gs)

        # Zimone discount on X-spells
        for c in list(gs.zones.hand):
            if c.name == ZIMONE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Mightform Harmonizer: landfall doubles creature power
        for c in list(gs.zones.hand):
            if c.name == MIGHTFORM and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Consult the Star Charts: draw
        for c in list(gs.zones.hand):
            if c.name == CONSULT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                edge_of_eternities._on_resolve(gs, CONSULT, c, opponent)
                break

        self._cast_all_castable(gs)

    def declare_attackers(self, gs, opponent):
        # All creatures attack (they have trample from Nev)
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
            assignments[id(biggest)] = [max(blockers, key=lambda c: safe_toughness(c))]
        return assignments

    def respond_to_spell(self, gs, opponent, spell): return None
    def end_step_actions(self, gs, opponent): pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if 'botanical' in n or 'rimewood' in n: return 0
            if 'forest' in n: return 1
            return 2
        gs.play_land(min(lands, key=score))
