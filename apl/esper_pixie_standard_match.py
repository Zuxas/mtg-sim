"""
apl/esper_pixie_standard_match.py — Esper Pixie (Standard)

Esper control/tempo using Kaito's ninjutsu + Nowhere to Run removal.
Win condition: Kaito Bane of Nightmares via ninjutsu, draw + Ninja tokens.

Key cards: Cecil Dark Knight (deathtouch), Kaito Bane of Nightmares
(ninjutsu unblocked attacker → draw + Ninja token), Nowhere to Run
(-3/-3 flash), Cosmogrand Zenith (token engine), Nurturing Pixie (ETB bounce).
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness
from apl.card_specs import duskmourn_spells, duskmourn_creatures, edge_of_eternities

KAITO        = "Kaito, Bane of Nightmares"
NOWHERE_TO_RUN= "Nowhere to Run"
COSMOGRAND   = "Cosmogrand Zenith"
NURTURING    = "Nurturing Pixie"
SEAM_RIP     = "Seam Rip"
CRYOGEN      = "Cryogen Relic"
MOMENTUM_BR  = "Momentum Breaker"
CECILDARK    = "Cecil, Dark Knight"

THREATS = {KAITO, CECILDARK, COSMOGRAND}


class EsperPixieMatchAPL(MatchAPL):
    name = "Esper Pixie"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in THREATS)
        if lands == 0: return False
        if lands >= 2 and threats >= 1: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        excess = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        to_bottom = excess[3:]
        filler = [c for c in hand if not c.is_land() and c not in to_bottom
                  and c.name not in THREATS]
        return (to_bottom + filler)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()

        # Cecil Dark Knight T1 — deathtouch 2/3 (costs B only)
        for c in list(gs.zones.hand):
            if c.name == CECILDARK and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Cecil, Dark Knight: 2/3 deathtouch (Darkness: self-drain)")
                break

        # Kaito T3+ (ninjutsu {1}{U}{B} from unblocked attacker)
        for c in list(gs.zones.hand):
            if c.name == KAITO and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs.zones.draw(1)
                # Create Ninja token
                tok = Card("Ninja Token", "{0}", 1, "Token Creature — Ninja")
                tok.power = "1"; tok.toughness = "1"
                tok.turn_entered = gs.turn; tok.summoning_sickness = True
                gs.zones.battlefield.append(tok)
                gs._log(f"  Kaito: ninjutsu, draw 1, create Ninja token")
                break

        # Cosmogrand Zenith
        for c in list(gs.zones.hand):
            if c.name == COSMOGRAND and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # Removal
        if opponent:
            threats = [x for x in opponent.zones.battlefield
                       if x.has(Tag.CREATURE) and not x.is_land() and safe_power(x) >= 2]
            if threats:
                t = max(threats, key=lambda x: safe_power(x))
                for c in list(gs.zones.hand):
                    if c.name == NOWHERE_TO_RUN and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        gs.cast_spell(c)
                        duskmourn_spells._nowhere_to_run(gs, opponent)
                        break
                    if c.name == SEAM_RIP and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        gs.cast_spell(c)
                        edge_of_eternities._on_resolve(gs, SEAM_RIP, c, opponent)
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
        # Cecil deathtouch blocks efficiently
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
