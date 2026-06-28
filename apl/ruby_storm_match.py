"""
apl/ruby_storm_match.py — Auto-generated Ruby Storm APL (Modern)
Generated from website playbook decklist. Needs manual audit for oracle accuracy.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

RUBY_MEDALLION = "Ruby Medallion"
DESPERATE_RITUAL = "Desperate Ritual"
MANAMORPHOSE = "Manamorphose"
PYRETIC_RITUAL = "Pyretic Ritual"
RECKLESS_IMPULSE = "Reckless Impulse"
WRENNS_RESOLVE = "Wrenn's Resolve"
GLIMPSE_THE_IMPOSSIB = "Glimpse the Impossible"
PAST_IN_FLAMES = "Past in Flames"
WISH = "Wish"
GRAPESHOT = "Grapeshot"

class RubyStormMatchAPL(MatchAPL):
    # R3 (2026-06-28): rewritten from the AUTO_GENERATED stub. Casts every spell via
    # gs.cast_spell so spells_cast_this_turn accrues + the storm handlers fire (storm
    # count). WANTS_STORM opts into the gated match-path main1 spell-damage sync.
    WANTS_STORM = True
    name = "Ruby Storm"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if not c.is_land() and c.has(Tag.CREATURE))
        interaction = sum(1 for c in hand if not c.is_land() and not c.has(Tag.CREATURE))
        if lands == 0: return False
        if lands > 5: return False
        if threats >= 1 and lands >= 2: return True
        if interaction >= 2 and lands >= 2: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[4:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        # R3 rewrite: route EVERY spell through gs.cast_spell so spells_cast_this_turn
        # accrues and the storm handlers (_grapeshot_spell etc.) fire. Cast accelerants /
        # cantrips first; hold the storm PAYOFF for last so its storm count is maximal.
        # (Goldfish RubyStormAPL already does this; the AUTO_GENERATED match stub bypassed
        # cast_spell with manual pay+graveyard+flat-2 damage, defeating storm entirely.)
        self._play_land_if_able(gs)
        gs.tap_lands()
        PAYOFFS = {GRAPESHOT, "Empty the Warrens", "Galvanic Relay"}

        # 1. Cast all non-payoff noncreature spells (rituals/cantrips), looping while a
        #    newly-affordable spell remains (a ritual may unlock the next cast).
        cast_any = True
        while cast_any:
            cast_any = False
            for c in list(gs.zones.hand):
                if c.is_land() or c.has(Tag.CREATURE) or c.name in PAYOFFS:
                    continue
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc) and gs.cast_spell(c):
                    cast_any = True

        # 2. Payoff LAST (maximal storm count). cast_spell -> _grapeshot_spell reads
        #    spells_cast_this_turn and deals `count` instances of 1 damage; the R3 gated
        #    main1 sync then propagates that to the opponent's match life total.
        for c in list(gs.zones.hand):
            if c.name in PAYOFFS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield
                if not c.is_land() and c.has(Tag.CREATURE)
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)
                   and not c.is_land() and safe_power(c) >= 3
                   and not getattr(c, 'tapped', False)]
        if blockers:
            biggest = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest) >= 3:
                assignments[id(biggest)] = [blockers[0]]
        return assignments

    def respond_to_spell(self, gs, opponent, spell): return None
    def end_step_actions(self, gs, opponent): pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if 'mesa' in n or 'strand' in n or 'delta' in n or 'tarn' in n or 'foothills' in n or 'flats' in n or 'rainforest' in n or 'catacombs' in n or 'heath' in n or 'mire' in n: return 0
            if 'foundry' in n or 'vents' in n or 'garden' in n or 'grave' in n or 'shrine' in n or 'fountain' in n or 'crypt' in n: return 1
            return 3
        gs.play_land(min(lands, key=score))
