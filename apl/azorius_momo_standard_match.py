"""
apl/azorius_momo_standard_match.py — Azorius Momo (Standard, PT SOS 2026)

White-Blue fliers/tempo. 4.3% of PT SOS field (14/325 players).
Key engine:
- Momo, Friendly Flier ({W} 1/1 flying): first flying spell each turn costs {1} less
- Haliya, Guided by Light ({2}{W}): gain 1 life whenever a creature/artifact enters
- Cosmogrand Zenith ({2}{W}): cast 2nd spell each turn -> 2 soldier tokens or draw+gain
- Sage of the Skies ({2}{W}): copy itself if 2nd spell this turn
- Starfield Shepherd ({3}{W}{W}): flying ETB tutor Plains or creature (MV <= life gained)
- Nurturing Pixie ({W} flying): ETB bounce own permanent for re-trigger
- Voice of Victory ({1}{W}): Mobilize 2 tokens on attack
- Doorkeeper Thrull ({1}{W}{B}): suppresses ETB triggers on opponents
"""
from data.card import Tag
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

MOMO       = "Momo, Friendly Flier"
HALIYA     = "Haliya, Guided by Light"
ZENITH     = "Cosmogrand Zenith"
SAGE       = "Sage of the Skies"
SHEPHERD   = "Starfield Shepherd"
PIXIE      = "Nurturing Pixie"
VOICE      = "Voice of Victory"
THRULL     = "Doorkeeper Thrull"
GET_LOST   = "Get Lost"
DRUM       = "Springleaf Drum"


class AzoriusMomoStandardMatchAPL(MatchAPL):
    name = "Azorius Momo"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in (MOMO, HALIYA, SAGE, VOICE))
        if lands == 0: return False
        if lands > 5: return False
        if threats >= 1 and lands >= 2: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[4:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        if opponent is not None:
            gs._match_opp = opponent
        self._play_land_if_able(gs)
        gs.tap_lands()

        # Cost reduction from Momo (first flying spell each turn costs {1} less)
        momo_on_board = any(c.name == MOMO for c in gs.zones.battlefield)
        if momo_on_board:
            gs.mana_pool.cost_reduction = max(gs.mana_pool.cost_reduction, 1)

        # 1. Removal: Get Lost on threats
        if opponent:
            threats = [c for c in opponent.zones.battlefield
                       if not c.is_land() and safe_power(c) >= 3]
            if threats:
                for c in list(gs.zones.hand):
                    if c.name == GET_LOST and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        target = max(threats, key=lambda x: safe_power(x))
                        gs.cast_spell(c)
                        if target in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(target)
                            opponent.zones.exile.append(target)
                        gs._log(f"  Get Lost: exile {target.name}")
                        break

        # 2. Deploy threats cheapest first
        spells_cast_this_main = 0
        for name in (MOMO, PIXIE, HALIYA, ZENITH, SAGE, VOICE, SHEPHERD, THRULL):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    spells_cast_this_main += 1
                    # Haliya: gain 1 life on ETB
                    if name == HALIYA:
                        gs.life += 1
                        gs._log(f"  Haliya ETB: gain 1 life (total {gs.life})")
                    # Cosmogrand Zenith: 2nd spell -> 2 Soldier tokens
                    elif name == ZENITH and spells_cast_this_main >= 2:
                        from data.card import Card as _C  # noqa: F811
                        for _ in range(2):
                            tok = _C("Soldier Token", mana_cost=None, cmc=0,
                                     type_line="Token Creature -- Human Soldier")
                            tok.power = '1'; tok.toughness = '1'
                            tok.summoning_sickness = True
                            gs.zones.battlefield.append(tok)
                        gs._log("  Cosmogrand Zenith: 2nd spell -> 2 Soldier tokens")
                    # Sage of the Skies: 2nd spell -> copy Sage
                    elif name == SAGE and spells_cast_this_main >= 2:
                        from data.card import Card as _C
                        copy = _C("Sage of the Skies", mana_cost=c.mana_cost,
                                  cmc=getattr(c, 'cmc', 0), type_line=getattr(c, 'type_line', ''))
                        copy.power = getattr(c, 'power', '2')
                        copy.toughness = getattr(c, 'toughness', '2')
                        copy.summoning_sickness = True
                        gs.zones.battlefield.append(copy)
                        gs._log("  Sage of the Skies: copy (2nd spell this turn)")
                    break

    def declare_attackers(self, gs, opponent):
        attackers = [c for c in gs.zones.battlefield
                     if not c.is_land() and c.has(Tag.CREATURE)
                     and not getattr(c, 'summoning_sickness', False)
                     and not getattr(c, 'tapped', False)]
        # Voice of Victory Mobilize 2
        if opponent:
            for c in attackers:
                if c.name == VOICE:
                    for _ in range(2):
                        from data.card import Card as _C
                        tok = _C("Warrior Token", mana_cost=None, cmc=0,
                                 type_line="Token Creature -- Warrior")
                        tok.power = '1'; tok.toughness = '1'
                        tok.summoning_sickness = False
                        gs.zones.battlefield.append(tok)
                        attackers.append(tok)
                    gs._log("  Voice Mobilize 2: 2 Warrior tokens attacking")
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()
                    and not getattr(c, 'tapped', False)
                    and safe_toughness(c) >= 2]
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
            if 'abandoned' in n or 'temple' in n: return 0
            if 'soulstone' in n: return 1
            return 3
        gs.play_land(min(lands, key=score))
