"""
apl/domain_zoo_match.py — Oracle-audited Domain Zoo APL (Modern)

Playbook engines (from Team Resolve):
A. Leyline Combo — T0 Leyline → all lands have all types → full domain instant
B. Ferocious Counter Wall — Stubborn Denial = hard counter with 4+ power
C. Phlage Recursion — escape from GY, 3 dmg + 3 life, hexproof under Scion

Key oracle mechanics:
- Leyline of the Guildpact: T0 if in opener. All nonland = all colors, all lands = all types
- Scion of Draco: {12} base, domain reduces by {2}/type. Gives keyword suite per color match
- Territorial Kavu: +1/+1 counter per color among lands (max 5 with domain)
- Leyline Binding: {5}{W} base, -1 per land type. Flash. Exile any nonland permanent
- Tribal Flames: {1}{R}, deals X where X = domain count (5 with full domain)
- Stubborn Denial: {U}, ferocious = hard counter noncreature spells
- Psychic Frog: {U}{B}, flying, discard to grow, surveil on damage
- Doorkeeper Thrull: {1}{W}, flash, ETB silence (no ETB triggers this turn)
- Phlage: hardcast 3 dmg sacrifice, escape {R}{R}{W}{W}+exile5 = permanent 6/6
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
PSYCHIC   = "Psychic Frog"
DOORKEEPER= "Doorkeeper Thrull"
LEYLINE_G = "Leyline of the Guildpact"
LEYLINE_B = "Leyline Binding"
BOLT      = "Lightning Bolt"
TRIBAL    = "Tribal Flames"
DENIAL    = "Stubborn Denial"
PRISMATIC = "Prismatic Ending"
THRABEN   = "Thraben Charm"

REMOVAL = {BOLT, LEYLINE_B, PRISMATIC, THRABEN}
CREATURES = {RAGAVAN, KAVU, PHLAGE, SCION, PSYCHIC, DOORKEEPER}


class DomainZooMatchAPL(MatchAPL):
    name = "Domain Zoo"
    win_condition_damage = 20
    max_turns = 10

    def __init__(self):
        self._leyline_active = False  # Leyline of the Guildpact on battlefield
        self._scion_active = False    # Scion of Draco on battlefield
        self._domain_count = 0        # number of basic land types (0-5)

    def _update_domain(self, gs):
        """Calculate domain count and track key permanents."""
        self._leyline_active = any(c.name == LEYLINE_G for c in gs.zones.battlefield)
        self._scion_active = any(c.name == SCION for c in gs.zones.battlefield)
        if self._leyline_active:
            self._domain_count = 5  # all lands have all types
        else:
            types = set()
            for c in gs.zones.battlefield:
                if not c.is_land(): continue
                tl = (getattr(c, 'type_line', '') or '').lower()
                for t in ('plains','island','swamp','mountain','forest'):
                    if t in tl: types.add(t)
            self._domain_count = len(types)

    def _scion_cost(self):
        """Scion costs {12} - {2} per domain count."""
        return max(2, 12 - self._domain_count * 2)

    def _binding_cost(self):
        """Leyline Binding costs {5}{W} - {1} per domain count. Min {W}."""
        return max(1, 6 - self._domain_count)

    def keep(self, hand, mulligans, on_play):
        """Playbook: Snap keep Leyline + creature + 2 lands. Snap mull no creatures."""
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in CREATURES)
        has_ley = any(c.name == LEYLINE_G for c in hand)
        has_scion = any(c.name == SCION for c in hand)
        has_kavu = any(c.name == KAVU for c in hand)
        
        if lands == 0: return False
        if threats == 0 and not has_ley: return False  # no pressure = mull
        if lands > 5: return False
        # Snap keeps from playbook
        if has_ley and threats >= 1 and lands >= 1: return True
        if has_scion and has_kavu and lands >= 2: return True
        if threats >= 2 and lands >= 2: return True
        if has_ley and lands >= 2: return True  # Leyline alone is powerful
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
        self._update_domain(gs)

        # 0. Leyline of the Guildpact — T0 if in opening hand (auto-deploy)
        for c in list(gs.zones.hand):
            if c.name == LEYLINE_G:
                if gs.turn <= 1:
                    # Free T0 deployment (oracle: enters before game begins)
                    gs.zones.hand.remove(c)
                    gs.zones.battlefield.append(c)
                    c.turn_entered = 0
                    self._update_domain(gs)
                    gs._log(f"  LEYLINE T0: all lands = all types, all creatures = all colors")
                elif gs.mana_pool.total() >= 4:
                    # Hardcast {3}{G} if drawn later
                    gs.cast_spell(c)
                    self._update_domain(gs)
                    gs._log(f"  Leyline hardcast: domain active")
                break

        avail = gs.mana_pool.total()

        # 1. Removal FIRST — kill their threats before developing
        if opponent:
            self._use_removal(gs, opponent)
            avail = gs.mana_pool.total()

        # 2. Deploy Ragavan T1 (haste, treasure on damage)
        for c in list(gs.zones.hand):
            if c.name == RAGAVAN and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                avail = gs.mana_pool.total()
                break

        # 3. Scion of Draco — domain cost reduction ({2} with full domain)
        scion_cost = self._scion_cost()
        for c in list(gs.zones.hand):
            if c.name == SCION and avail >= scion_cost:
                gs.zones.hand.remove(c)
                gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn; c.summoning_sickness = True
                self._scion_active = True
                gs._log(f"  Scion of Draco: 4/4 flying (cost {scion_cost} with domain={self._domain_count})")
                gs._log(f"    → All creatures gain: hexproof, lifelink, first strike, trample, vigilance")
                avail -= scion_cost
                break

        # 4. Territorial Kavu ({R}{G}) — size = domain count
        for c in list(gs.zones.hand):
            if c.name == KAVU and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                # Set domain-boosted P/T BEFORE deploying
                if self._domain_count >= 3:
                    c.power = str(self._domain_count)
                    c.toughness = str(self._domain_count)
                gs.cast_spell(c)
                gs._log(f"  Kavu: {safe_power(c)}/{safe_toughness(c)} with domain={self._domain_count}")
                avail = gs.mana_pool.total()
                break

        # 5. Psychic Frog ({U}{B}) — flying, discard to grow
        for c in list(gs.zones.hand):
            if c.name == PSYCHIC and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                avail = gs.mana_pool.total()
                break

        # 6. Doorkeeper Thrull ({1}{W}) — flash, ETB silence
        for c in list(gs.zones.hand):
            if c.name == DOORKEEPER and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                avail = gs.mana_pool.total()
                break

        # 7. Phlage — escape from GY or hardcast
        # Escape: {R}{R}{W}{W} + exile 5 = permanent 6/6
        gy_phlages = [c for c in gs.zones.graveyard if c.name == PHLAGE]
        other_gy = len(gs.zones.graveyard) - len(gy_phlages)
        if gy_phlages and other_gy >= 5 and avail >= 4:
            phlage = gy_phlages[0]
            for _ in range(5):
                non_p = [x for x in gs.zones.graveyard if x.name != PHLAGE]
                if non_p:
                    gs.zones.graveyard.remove(non_p[0])
                    gs.zones.exile.append(non_p[0])
            gs.zones.graveyard.remove(phlage)
            gs.zones.battlefield.append(phlage)
            phlage.turn_entered = gs.turn; phlage.summoning_sickness = True
            if opponent: gs.damage_dealt += 3
            gs.life += 3
            gs._log(f"  PHLAGE ESCAPE: 6/6 permanent + 3 dmg + 3 life")
            if self._scion_active:
                gs._log(f"    → Scion gives hexproof, lifelink, first strike, trample")
        else:
            for c in list(gs.zones.hand):
                if c.name == PHLAGE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    if opponent:
                        opp_cr = [x for x in opponent.zones.battlefield
                                 if not x.is_land() and x.has(Tag.CREATURE) and safe_toughness(x) <= 3]
                        if opp_cr:
                            t = max(opp_cr, key=lambda x: safe_power(x))
                            opponent.zones.battlefield.remove(t)
                            opponent.zones.graveyard.append(t)
                            gs._log(f"  Phlage hardcast: kill {t.name} + 3 life (sacrifice)")
                        else:
                            gs.damage_dealt += 3
                            gs._log(f"  Phlage hardcast: 3 face + 3 life (sacrifice)")
                    else:
                        gs.damage_dealt += 3
                    gs.life += 3
                    gs.zones.graveyard.append(c)
                    break

        avail = gs.mana_pool.total()

        # 8. Tribal Flames — {1}{R}, deals domain count damage (5 with full domain!)
        # Playbook: "Two Flames = 10 damage from hand. At 20 life: lethal with one attack."
        if opponent:
            for c in list(gs.zones.hand):
                if c.name == TRIBAL and avail >= 2:
                    gs.mana_pool.pay("{1}{R}", 2) if gs.mana_pool.can_pay("{1}{R}", 2) else None
                    gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                    dmg = self._domain_count  # 5 with full domain
                    # Target: kill big creature if possible, otherwise FACE
                    opp_cr = [x for x in opponent.zones.battlefield
                             if not x.is_land() and x.has(Tag.CREATURE) 
                             and safe_toughness(x) <= dmg and safe_power(x) >= 3]
                    if opp_cr:
                        t = max(opp_cr, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(t)
                        opponent.zones.graveyard.append(t)
                        gs._log(f"  Tribal Flames: {dmg} dmg → kill {t.name}")
                    else:
                        gs.damage_dealt += dmg
                        gs._log(f"  Tribal Flames: {dmg} FACE ({gs.damage_dealt} total)")
                    avail = gs.mana_pool.total()
                    # Don't break — cast ALL Flames for reach

        # 9. Bolt face — ALL bolts when closing or no creatures to kill
        for c in list(gs.zones.hand):
            if c.name == BOLT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                if opponent:
                    opp_cr = [x for x in opponent.zones.battlefield
                             if not x.is_land() and x.has(Tag.CREATURE) and safe_power(x) >= 3
                             and safe_toughness(x) <= 3]
                    if opp_cr:
                        t = max(opp_cr, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(t)
                        opponent.zones.graveyard.append(t)
                        gs.mana_pool.pay(c.mana_cost, c.cmc)
                        gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                        gs._log(f"  Bolt: kill {t.name}")
                        continue
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                gs.damage_dealt += 3
                gs._log(f"  Bolt face: 3 dmg ({gs.damage_dealt} total)")

        # 10. Fill remaining with creatures
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and c.name not in (PHLAGE, SCION):
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)

    def _use_removal(self, gs, opponent):
        """Remove opponent's best creature. Priority: Binding (exile any) > Bolt (3 dmg)."""
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures: return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 2: return

        # Leyline Binding — exile anything for domain-reduced cost (flash!)
        binding_cost = self._binding_cost()
        for c in list(gs.zones.hand):
            if c.name == LEYLINE_B and gs.mana_pool.total() >= binding_cost:
                gs.mana_pool.flex -= min(binding_cost, gs.mana_pool.flex)
                gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                if target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.exile.append(target)
                gs._log(f"  Binding: exile {target.name} (cost {binding_cost} with domain={self._domain_count})")
                return

        # Bolt — kills toughness ≤3
        if safe_toughness(target) <= 3:
            for c in list(gs.zones.hand):
                if c.name == BOLT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                    if target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.graveyard.append(target)
                    gs._log(f"  Bolt: kill {target.name}")
                    return

    def declare_attackers(self, gs, opponent):
        """Attack with everything. Scion gives vigilance → can attack AND block.
        Kavu size is domain_count. Phlage attack trigger: 3 dmg + 3 life."""
        self._update_domain(gs)
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land(): continue
            if not c.has(Tag.CREATURE): continue
            if getattr(c, 'summoning_sickness', False): continue
            if getattr(c, 'tapped', False): continue
            attackers.append(c)
        
        # Phlage attack trigger: 3 damage + 3 life
        for a in attackers:
            if a.name == PHLAGE:
                if opponent:
                    opp_cr = [x for x in opponent.zones.battlefield
                             if x.has(Tag.CREATURE) and not x.is_land() and safe_toughness(x) <= 3]
                    if opp_cr:
                        t = max(opp_cr, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(t)
                        opponent.zones.graveyard.append(t)
                        gs._log(f"  Phlage attack: kill {t.name} + 3 life")
                    else:
                        gs.damage_dealt += 3
                        gs._log(f"  Phlage attack: 3 face + 3 life ({gs.damage_dealt} total)")
                gs.life += 3
        
        # Ragavan combat damage: treasure + exile top card
        for a in attackers:
            if a.name == RAGAVAN:
                gs._log(f"  Ragavan attacks (treasure on damage)")
        
        # Scion keyword grants: lifelink calculated on DAMAGE dealt (not attack power)
        # The combat engine handles actual damage; we add lifelink proportionally
        if self._scion_active:
            # Approximate: gain life = creatures attacking * avg damage getting through
            unblocked_power = sum(safe_power(a) for a in attackers) // 2  # conservative estimate
            gs.life += unblocked_power
            gs._log(f"  Scion lifelink: ~{unblocked_power} life from combat")
        
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        """Block with Scion's vigilance creatures (they can attack AND block)."""
        assignments = {}
        if not attackers: return assignments
        if self._scion_active:
            # With Scion: all creatures have vigilance, so they're untapped after attacking
            blockers = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)
                       and not c.is_land() and not getattr(c, 'tapped', False)]
        else:
            blockers = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)
                       and not c.is_land() and not getattr(c, 'tapped', False)
                       and safe_power(c) >= 3]
        if blockers:
            biggest = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest) >= 3:
                best_blocker = max(blockers, key=lambda c: safe_toughness(c))
                assignments[id(biggest)] = [best_blocker]
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        """Stubborn Denial — hard counter noncreature spells with ferocious.
        Playbook: '{U} hard counter with ferocious, no pay-{1} escape clause.'
        """
        if not spell: return None
        has_ferocious = any(safe_power(c) >= 4 for c in gs.zones.battlefield
                           if not c.is_land() and c.has(Tag.CREATURE))
        if has_ferocious:
            for c in list(gs.zones.hand):
                if c.name == DENIAL and gs.mana_pool.total() >= 1:
                    gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                    gs._log(f"  Stubborn Denial: HARD counter {spell.name} (ferocious)")
                    return c
        return None

    def end_step_actions(self, gs, opponent): pass

    def _play_land_if_able(self, gs):
        """Fetch lands first (fix colors), then duals, then basics."""
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if 'mesa' in n or 'foothills' in n or 'strand' in n or 'tarn' in n or 'flats' in n:
                return 0  # fetches first
            if 'arena' in n: return 1  # haste land
            if 'foundry' in n or 'vents' in n or 'garden' in n or 'crypt' in n: return 2
            if 'triome' in n or 'headquarters' in n: return 3
            return 5
        gs.play_land(min(lands, key=score))
