"""
apl/eldrazi_ramp_match.py — Match-aware Eldrazi Ramp APL (Modern)

Key mechanics:
1. Eldrazi Temple: adds 2 mana for Eldrazi spells
2. Utopia Sprawl + Talisman: ramp into big Eldrazi fast
3. Emrakul, the Promised End: take opponent's turn (game-ending)
4. Kozilek's Return: instant-speed 5 damage sweeper (triggered by big Eldrazi)
5. Sowing Mycospawn: ramp + tutor for Eldrazi
6. World Breaker: 5/7 reach, exile a permanent on ETB
"""
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

EMRAKUL    = "Emrakul, the Promised End"
WORLD_BREAKER = "World Breaker"
DEVOURER   = "Devourer of Destiny"
SIRE       = "Sire of Seven Deaths"
MYCOSPAWN  = "Sowing Mycospawn"
KOZ_RETURN = "Kozilek's Return"
KOZ_CMD    = "Kozilek's Command"
UGIN       = "Ugin, Eye of the Storms"
TALISMAN   = "Talisman of Impulse"
SPRAWL     = "Utopia Sprawl"
STIRRINGS  = "Ancient Stirrings"
RUMBLE     = "Malevolent Rumble"
FORMIDABLE = "Formidable Speaker"


class EldraziRampMatchAPL(MatchAPL):
    name = "Eldrazi Ramp"
    win_condition_damage = 20
    max_turns = 12
    _ramp_bonus = 0

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        ramp = sum(1 for c in hand if c.name in {TALISMAN, SPRAWL, MYCOSPAWN})
        threats = sum(1 for c in hand if c.name in {EMRAKUL, WORLD_BREAKER, DEVOURER, SIRE})
        if lands == 0: return False
        if lands >= 2 and ramp >= 1: return True
        if lands >= 3 and threats >= 1: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[4:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()
        gs.mana_pool.flex += self._ramp_bonus
        self._ramp_bonus = 0

        # 1. Ramp: Talisman, Utopia Sprawl
        for c in list(gs.zones.hand):
            if c.name == TALISMAN and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c); self._ramp_bonus += 1; break
        for c in list(gs.zones.hand):
            if c.name == SPRAWL and gs.mana_pool.total() >= 1:
                gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                self._ramp_bonus += 1; break

        # 2. Kozilek's Return as removal (instant 2 dmg, or 5 from GY)
        if opponent:
            opp_creatures = [c for c in opponent.zones.battlefield
                             if not c.is_land() and c.has(Tag.CREATURE)]
            if len(opp_creatures) >= 2:
                for c in list(gs.zones.hand):
                    if c.name == KOZ_RETURN and gs.mana_pool.total() >= 3:
                        gs.mana_pool.pay("{2}{R}", 3)
                        gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                        for creature in list(opp_creatures):
                            if safe_toughness(creature) <= 2 and creature in opponent.zones.battlefield:
                                opponent.zones.battlefield.remove(creature)
                                opponent.zones.graveyard.append(creature)
                        gs._log(f"  Kozilek's Return — sweeper")
                        break

        # 3. Big Eldrazi threats
        avail = gs.mana_pool.total()
        for name in (MYCOSPAWN, FORMIDABLE, DEVOURER, WORLD_BREAKER, SIRE, UGIN):
            for c in list(gs.zones.hand):
                if c.name == name and avail >= getattr(c, 'cmc', 99):
                    gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                    c.turn_entered = gs.turn; c.summoning_sickness = True
                    avail -= getattr(c, 'cmc', 0)
                    if name == WORLD_BREAKER and opponent:
                        # Exile target permanent
                        targets = [x for x in opponent.zones.battlefield if not x.is_land()]
                        if targets:
                            t = max(targets, key=lambda x: safe_power(x))
                            opponent.zones.battlefield.remove(t); opponent.zones.exile.append(t)
                            gs._log(f"  World Breaker → exile {t.name}")
                    break

        # 4. Emrakul — take opponent's turn (game-ending, simulate as instant win)
        for c in list(gs.zones.hand):
            if c.name == EMRAKUL:
                # Cost reduction: -1 per card type in GY
                types_in_gy = set()
                for g in gs.zones.graveyard:
                    tl = (getattr(g, 'type_line', '') or '').lower()
                    for t in ('creature','instant','sorcery','artifact','enchantment','planeswalker','land'):
                        if t in tl: types_in_gy.add(t)
                reduction = len(types_in_gy)
                effective_cost = max(4, 13 - reduction)  # base 13, min 4
                if avail >= effective_cost:
                    gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                    c.turn_entered = gs.turn; c.summoning_sickness = False  # haste
                    gs._log(f"  EMRAKUL! (cost {effective_cost}, reduced by {reduction})")
                    break

        # 5. Remaining
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield
                if not c.is_land() and c.has(Tag.CREATURE)
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        # Block with big Eldrazi (they're huge)
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)
                    and not c.is_land() and safe_power(c) >= 5
                    and not getattr(c, 'tapped', False)]
        if blockers and attackers:
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
            if 'temple' in c.name.lower(): return 0
            if 'labyrinth' in c.name.lower(): return 1
            return 3
        gs.play_land(min(lands, key=score))
