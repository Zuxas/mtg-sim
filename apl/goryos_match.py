"""
apl/goryos_match.py — Match-aware Goryo's Vengeance/Esper Reanimator APL

Key mechanics:
1. Goryo's Vengeance: instant-speed reanimate legendary creature (haste, exile at EOT)
2. Atraxa, Grand Unifier: 7/7 flying vigilance, ETB draw 10 (keep up to 7)
3. Griselbrand: 7/7 flying lifelink, pay 7 life to draw 7
4. Psychic Frog: discard outlet + grows when cards go to GY
5. Faithful Mending: draw 2 discard 2 (puts fatties in GY)
6. Solitude: pitch removal (same as Blink)
7. Force of Negation: free counterspell (pitch blue card)
8. Gran-Gran: enters as copy of creature in GY
"""
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

GORYOS     = "Goryo's Vengeance"
ATRAXA     = "Atraxa, Grand Unifier"
GRISELBRAND = "Griselbrand"
ULAMOG     = "Ulamog, the Defiler"
FROG       = "Psychic Frog"
MENDING    = "Faithful Mending"
TAINTED    = "Tainted Indulgence"
SOLITUDE   = "Solitude"
FORCE      = "Force of Negation"
EPHEMERATE = "Ephemerate"
GRAN_GRAN  = "Gran-Gran"
EMPEROR    = "Emperor of Bones"
THOUGHTSEIZE = "Thoughtseize"
PRISMATIC  = "Prismatic Ending"
QUANTUM    = "Quantum Riddler"

BIG_TARGETS = {ATRAXA, GRISELBRAND, ULAMOG}
DISCARD_OUTLETS = {FROG, MENDING, TAINTED}

class GoryosMatchAPL(MatchAPL):
    name = "Goryos Vengeance"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        has_goryos = any(c.name == GORYOS for c in hand)
        has_target = any(c.name in BIG_TARGETS for c in hand)
        has_discard = any(c.name in DISCARD_OUTLETS for c in hand)
        has_frog = any(c.name == FROG for c in hand)
        if lands == 0: return False
        if has_goryos and (has_target or has_discard) and lands >= 1: return True
        if has_frog and lands >= 2: return True  # fair game plan
        if has_discard and has_target and lands >= 1: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[3:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()

        # PRIORITY 1: COMBO — get fatty in GY then Goryo's it
        gy_targets = [c for c in gs.zones.graveyard if c.name in BIG_TARGETS]
        hand_targets = [c for c in gs.zones.hand if c.name in BIG_TARGETS]
        has_goryos = any(c.name == GORYOS for c in gs.zones.hand)

        # 1A. Discard fatty via Psychic Frog (free discard outlet)
        if hand_targets and not gy_targets:
            frog_on_board = any(c.name == FROG for c in gs.zones.battlefield
                                if not getattr(c, 'summoning_sickness', False))
            if frog_on_board:
                target = hand_targets[0]
                gs.zones.hand.remove(target); gs.zones.graveyard.append(target)
                gy_targets = [target]

        # 1B. Discard via Faithful Mending / Tainted Indulgence
        hand_targets = [c for c in gs.zones.hand if c.name in BIG_TARGETS]
        if hand_targets and not gy_targets:
            for c in list(gs.zones.hand):
                if c.name in (MENDING, TAINTED) and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                    gs.zones.draw(2)
                    to_discard = [x for x in gs.zones.hand if x.name in BIG_TARGETS]
                    if to_discard:
                        gs.zones.hand.remove(to_discard[0]); gs.zones.graveyard.append(to_discard[0])
                    worst = min(gs.zones.hand, key=lambda x: 0 if x.name == GORYOS else getattr(x,'cmc',5), default=None)
                    if worst and worst.name != GORYOS:
                        gs.zones.hand.remove(worst); gs.zones.graveyard.append(worst)
                    gy_targets = [c for c in gs.zones.graveyard if c.name in BIG_TARGETS]
                    break

        # 1C. GORYO'S VENGEANCE — reanimate NOW
        gy_targets = [c for c in gs.zones.graveyard if c.name in BIG_TARGETS]
        if gy_targets and gs.mana_pool.total() >= 2:
            for c in list(gs.zones.hand):
                if c.name == GORYOS:
                    target = gy_targets[0]
                    gs.mana_pool.pay("{1}{B}", 2)
                    gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                    gs.zones.graveyard.remove(target)
                    gs.zones.battlefield.append(target)
                    target.turn_entered = gs.turn; target.summoning_sickness = False
                    if target.name == ATRAXA:
                        gs.zones.draw(min(7, 40 - len(gs.zones.hand)))
                    elif target.name == GRISELBRAND:
                        gs.zones.draw(7); gs.life -= 7
                    break

        # 2. Deploy Psychic Frog ASAP (discard outlet + threat)
        for c in list(gs.zones.hand):
            if c.name == FROG and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c); break

        # 3. Thoughtseize (only if combo not ready)
        if opponent and not has_goryos and gs.turn <= 2:
            for c in list(gs.zones.hand):
                if c.name == THOUGHTSEIZE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                    gs.life -= 2
                    opp_nl = [x for x in opponent.zones.hand if not x.is_land()]
                    if opp_nl:
                        t = max(opp_nl, key=lambda x: getattr(x,'cmc',0))
                        opponent.zones.hand.remove(t); opponent.zones.graveyard.append(t)
                    break

        # 4. Solitude pitch on big threats
        if opponent:
            opp_c = [c for c in opponent.zones.battlefield
                     if not c.is_land() and c.has(Tag.CREATURE) and safe_power(c) >= 3]
            if opp_c:
                target = max(opp_c, key=lambda c: safe_power(c))
                sol = next((c for c in gs.zones.hand if c.name == SOLITUDE), None)
                if sol:
                    whites = [c for c in gs.zones.hand if c != sol and c.name not in BIG_TARGETS
                              and 'W' in (getattr(c,'mana_cost','') or '')]
                    if whites:
                        pitch = whites[0]
                        gs.zones.hand.remove(sol); gs.zones.hand.remove(pitch)
                        gs.zones.exile.append(pitch)
                        gs.zones.battlefield.append(sol); sol.turn_entered = gs.turn; sol.summoning_sickness = True
                        if target in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(target); opponent.zones.exile.append(target)
                        opponent.life += safe_power(target)

        # 5. Fair game: Quantum Riddler, Gran-Gran, Emperor
        for name in (QUANTUM, GRAN_GRAN, EMPEROR):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c); break

        # 6. Remaining (not big targets)
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and c.name not in BIG_TARGETS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def respond_to_spell(self, gs, opponent, spell):
        for c in gs.zones.hand:
            if c.name == FORCE:
                blues = [x for x in gs.zones.hand if x != c and 'U' in (getattr(x,'mana_cost','') or '')]
                if blues: return c
        return None

    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield
                if not c.is_land() and c.has(Tag.CREATURE)
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers): return {}
    def end_step_actions(self, gs, opponent): pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        gs.play_land(min(lands, key=lambda c: c.name))
