"""
apl/boros_aggro_standard_match.py — Boros Aggro (Standard, April 2026)

Leyline of Resonance build: every instant/sorcery you cast gets copied.
Win condition: pump spells × 2 + Slickshot Show-Off flying damage.

Replaced pre-ban build (Kumano/Swiftspear) with current Leyline shell.
Key new cards: Leyline of Resonance (copy all spells), Emberheart Challenger
(haste prowess), Burnout Bashtronaut (menace + speed), Slickshot (fly +2/+0).
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness
from apl.card_specs import duskmourn_spells

LEYLINE_RES    = "Leyline of Resonance"
SLICKSHOT      = "Slickshot Show-Off"
EMBERHEART     = "Emberheart Challenger"
BURNOUT_BASH   = "Burnout Bashtronaut"
STADIUM_HEAD   = "Stadium Headliner"
BURST_LIGHT    = "Burst Lightning"
FULL_BORE      = "Full Bore"
HONOR          = "Honor"
MIGHT_MEEK     = "Might of the Meek"
TURN_INSIDE    = "Turn Inside Out"

THREATS = {SLICKSHOT, EMBERHEART, BURNOUT_BASH, STADIUM_HEAD}
PUMP_SPELLS = {FULL_BORE, HONOR, MIGHT_MEEK, BURST_LIGHT, TURN_INSIDE}


class BorosAggroMatchAPL(MatchAPL):
    name = "Boros Aggro"
    win_condition_damage = 20
    max_turns = 7

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        has_leyline = any(c.name == LEYLINE_RES for c in hand)
        has_threat = any(c.name in THREATS for c in hand)
        if lands == 0 and not has_leyline: return False
        if has_threat and lands >= 1: return True
        if has_leyline: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        excess = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        to_bottom = excess[3:]
        filler = [c for c in hand if not c.is_land() and c not in to_bottom
                  and c.name not in THREATS and c.name != LEYLINE_RES]
        return (to_bottom + filler)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        if opponent is not None:
            gs._match_opp = opponent
        self._play_land_if_able(gs)
        gs.tap_lands()
        leyline_active = duskmourn_spells.is_leyline_active(gs, LEYLINE_RES)

        # Leyline from opening hand
        duskmourn_spells.cast_leyline_if_opening(gs, LEYLINE_RES)

        # Deploy haste creatures first (attack this turn)
        for name in (SLICKSHOT, EMBERHEART, BURNOUT_BASH, STADIUM_HEAD):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    # Slickshot pumps from noncreature spells already cast
                    break

        # Pump spells (each copied if Leyline active)
        copies = 2 if leyline_active else 1
        for spell_name in (FULL_BORE, HONOR, MIGHT_MEEK, BURST_LIGHT):
            for c in list(gs.zones.hand):
                if c.name == spell_name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    if spell_name == BURST_LIGHT:
                        gs.damage_dealt += 2 * copies
                    elif spell_name == HONOR:
                        critters = [x for x in gs.zones.battlefield
                                    if x.has(Tag.CREATURE) and not x.is_land()]
                        if critters:
                            max(critters, key=lambda x: safe_power(x)).counters = (
                                getattr(max(critters, key=lambda x: safe_power(x)),'counters',0) + copies)
                        gs.zones.draw(copies)
                    # Pump Slickshot +2/+0 per noncreature spell cast
                    for sl in gs.zones.battlefield:
                        if sl.name == SLICKSHOT:
                            sl.counters = getattr(sl,'counters',0) + 2
                    break

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
            if 'foundry' in n or 'vantage' in n: return 0
            if 'mountain' in n: return 1
            return 2
        gs.play_land(min(lands, key=score))
