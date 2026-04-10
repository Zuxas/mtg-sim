"""
apl/domain_zoo_match.py — Match-aware Domain Zoo APL (Modern)

Key match-mode changes from goldfish:
1. Leyline Binding is LIVE — exile any nonland permanent for {W} with domain
2. Stubborn Denial counters key spells (ferocious active with Kavu 5/5)
3. Prismatic Ending removes small threats
4. Bolt targets creatures early, face late
5. Block strategically — Scion gives first strike/vigilance/lifelink with domain

Domain Zoo is the aggro-midrange deck: T1 Ragavan, T2 Kavu (5/5 with domain),
T3 Scion (gives all multicolor creatures keywords). Wins by deploying
oversized threats that also interact with removal + countermagic.
"""

from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

RAGAVAN   = "Ragavan, Nimble Pilferer"
KAVU      = "Territorial Kavu"
PHLAGE    = "Phlage, Titan of Fire's Fury"
SCION     = "Scion of Draco"
LEYLINE_G = "Leyline of the Guildpact"
LEYLINE_B = "Leyline Binding"
BOLT      = "Lightning Bolt"
DENIAL    = "Stubborn Denial"
PRISMATIC = "Prismatic Ending"

REMOVAL = {BOLT, LEYLINE_B, PRISMATIC}


class DomainZooMatchAPL(MatchAPL):
    name = "Domain Zoo"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in {RAGAVAN, KAVU, PHLAGE, SCION})
        removal = sum(1 for c in hand if c.name in REMOVAL)
        has_ley = any(c.name == LEYLINE_G for c in hand)
        if lands == 0:
            return False
        if has_ley and threats >= 1 and lands >= 1:
            return True
        if lands >= 2 and threats >= 1 and removal >= 1:
            return True
        if lands >= 2 and threats >= 2:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        to_bottom = []
        if len(lands) > 3:
            to_bottom.extend(lands[3:])
        for c in spells:
            if len(to_bottom) >= n:
                break
            if c not in to_bottom:
                to_bottom.append(c)
        return to_bottom[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """Deploy threats + use removal on opponent creatures."""
        self._play_land_if_able(gs)

        # Leyline of the Guildpact (free if in opening hand, otherwise cast)
        for c in list(gs.zones.hand):
            if c.name == LEYLINE_G:
                if gs.turn == 1 and getattr(c, 'cmc', 4) == 0:
                    gs.zones.hand.remove(c)
                    gs.zones.battlefield.append(c)
                    c.turn_entered = gs.turn
                elif gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                break

        # Use removal on opponent's best creature
        if opponent:
            self._use_removal(gs, opponent)

        # Deploy threats by priority
        for name in (RAGAVAN, KAVU, SCION, PHLAGE):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # Fill curve with remaining creatures
        changed = True
        while changed:
            changed = False
            castable = [c for c in gs.zones.hand
                        if not c.is_land() and c.name not in REMOVAL
                        and hasattr(c, 'cmc') and c.cmc > 0
                        and c.cmc <= gs.mana_pool.total()]
            if castable:
                spell = min(castable, key=lambda c: c.cmc)
                if gs.cast_spell(spell):
                    changed = True
                else:
                    break

        # Bolt face if no creatures to remove and we have mana
        if not opponent or not any(not c.is_land() for c in opponent.zones.battlefield):
            for c in list(gs.zones.hand):
                if c.name == BOLT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.damage_dealt += 3
                    gs._log(f"  Bolt face: 3 dmg ({gs.damage_dealt} total)")
                    break

    def _use_removal(self, gs: GameState, opponent: GameState):
        """Remove opponent's best creature."""
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures:
            return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 2:
            return

        # Leyline Binding — exile anything for 1 mana with domain
        for c in list(gs.zones.hand):
            if c.name == LEYLINE_B:
                # With domain, costs {W} (1 mana). Without, costs {5}{W}.
                has_domain = any(x.name == LEYLINE_G for x in gs.zones.battlefield)
                cost = 1 if has_domain else 6
                if gs.mana_pool.total() >= cost:
                    gs.mana_pool.flex -= min(cost, gs.mana_pool.flex)
                    gs.zones.hand.remove(c)
                    gs.zones.battlefield.append(c)
                    c.turn_entered = gs.turn
                    if target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.exile.append(target)
                    gs._log(f"  Leyline Binding → exile {target.name}")
                    return

        # Bolt — kills toughness ≤3
        if safe_toughness(target) <= 3:
            for c in list(gs.zones.hand):
                if c.name == BOLT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    if target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.graveyard.append(target)
                    gs._log(f"  Bolt → kill {target.name}")
                    return

        # Prismatic Ending — exile CMC ≤ X where X = colors of mana spent
        for c in list(gs.zones.hand):
            if c.name == PRISMATIC and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                target_cmc = getattr(target, 'cmc', 0)
                if target_cmc <= 3:
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    if target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.exile.append(target)
                    gs._log(f"  Prismatic Ending → exile {target.name}")
                    return

    def declare_attackers(self, gs, opponent):
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land():
                continue
            if getattr(c, 'summoning_sickness', False):
                continue
            if getattr(c, 'tapped', False):
                continue
            if c.has(Tag.CREATURE):
                attackers.append(c)
        return attackers

    def declare_blockers(self, gs, opponent_gs, attackers):
        return {}

    def respond_to_spell(self, gs, opponent, spell):
        """Use Stubborn Denial if we have ferocious (4+ power creature)."""
        has_ferocious = any(safe_power(c) >= 4 for c in gs.zones.battlefield
                           if not c.is_land())
        if has_ferocious:
            for c in gs.zones.hand:
                if c.name == DENIAL and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    return c
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        def score(c):
            n = c.name.lower()
            if 'mesa' in n or 'foothills' in n or 'heath' in n or 'tarn' in n:
                return 0
            if 'foundry' in n or 'ground' in n or 'garden' in n:
                return 1
            return 3
        best = min(lands, key=score)
        gs.play_land(best)
