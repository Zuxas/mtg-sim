"""
apl/murktide_match.py — Match-aware Dimir Murktide APL (Modern)

Match changes from goldfish:
1. Counterspells are LIVE (Counterspell, Spell Pierce, Spell Snare)
2. Bolt/Unholy Heat target creatures (not face) until opponent's board is clear
3. Hold up counter mana instead of tapping out — deploy threats on opponent's end step
4. Murktide Regent finishes after establishing tempo control
5. Cantrips fill GY for Murktide delve AND delirium for DRC/Unholy Heat
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

RAGAVAN    = "Ragavan, Nimble Pilferer"
DRC        = "Dragon's Rage Channeler"
MURKTIDE   = "Murktide Regent"
BOLT       = "Lightning Bolt"
UNHOLY     = "Unholy Heat"
COUNTERSPELL = "Counterspell"
SPELL_PIERCE = "Spell Pierce"
SPELL_SNARE  = "Spell Snare"
PREORDAIN  = "Preordain"
OPT        = "Opt"
CONSIDER   = "Consider"
BAUBLE     = "Mishra's Bauble"
ITERATION  = "Expressive Iteration"

CANTRIPS = {PREORDAIN, OPT, CONSIDER, BAUBLE, ITERATION}
COUNTERS = {COUNTERSPELL, SPELL_PIERCE, SPELL_SNARE}
REMOVAL  = {BOLT, UNHOLY}


class MurktideMatchAPL(MatchAPL):
    name = "Dimir Murktide"
    win_condition_damage = 20
    max_turns = 12
    _treasures = 0

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in {RAGAVAN, DRC, MURKTIDE})
        interaction = sum(1 for c in hand if c.name in COUNTERS | REMOVAL)
        cantrips = sum(1 for c in hand if c.name in CANTRIPS)
        if lands == 0: return False
        if lands > 4: return False
        # Tempo hand: threat + interaction + cantrip
        if threats >= 1 and interaction >= 1 and lands >= 1: return True
        if threats >= 1 and cantrips >= 1 and lands >= 2: return True
        if lands >= 2 and threats >= 1: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        pool = lands[3:] + spells
        return pool[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """Tempo: deploy threat, hold interaction, counter key spells."""
        if self._treasures > 0:
            use = min(self._treasures, 2)
            gs.mana_pool.flex += use
            self._treasures -= use

        self._play_land_if_able(gs)

        # 1. Remove opponent's best creature
        if opponent:
            self._use_removal(gs, opponent)

        # 2. Deploy ONE cheap threat (Ragavan T1, DRC T1-T2)
        has_threat = any(c.name in {RAGAVAN, DRC, MURKTIDE}
                         for c in gs.zones.battlefield if not c.is_land())
        if not has_threat:
            for name in (RAGAVAN, DRC):
                for c in list(gs.zones.hand):
                    if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        gs.cast_spell(c)
                        has_threat = True
                        break
                if has_threat: break

        # 3. Cantrips to fill GY (for Murktide delve and delirium)
        for c in list(gs.zones.hand):
            if c.name in CANTRIPS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                if c.name == BAUBLE:
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.zones.draw(1)
                else:
                    gs.cast_spell(c)
                    gs.zones.draw(1)
                break

        # 4. Murktide Regent — delve finisher
        for c in list(gs.zones.hand):
            if c.name == MURKTIDE:
                gy_size = len(gs.zones.graveyard)
                delve = min(gy_size, 5)
                effective_cost = 7 - delve
                if gs.mana_pool.total() >= effective_cost:
                    # Pay mana
                    to_pay = effective_cost
                    while to_pay > 0 and gs.mana_pool.total() > 0:
                        gs.mana_pool.flex = max(0, gs.mana_pool.flex - 1)
                        to_pay -= 1
                    # Exile cards for delve
                    for _ in range(delve):
                        if gs.zones.graveyard:
                            exiled = gs.zones.graveyard.pop(0)
                            gs.zones.exile.append(exiled)
                    gs.zones.hand.remove(c)
                    gs.zones.battlefield.append(c)
                    c.turn_entered = gs.turn
                    c.summoning_sickness = True
                    c.power = str(8 + delve)
                    c.toughness = str(8 + delve)
                    gs._log(f"  Murktide Regent: {c.power}/{c.toughness} (delved {delve})")
                break

        # 5. DON'T tap out — hold mana for counterspells
        # (remaining mana left open intentionally)

    def _use_removal(self, gs: GameState, opponent: GameState):
        """Bolt/Unholy Heat on opponent's biggest creature."""
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures: return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 2: return

        # Unholy Heat first (6 damage with delirium)
        for c in list(gs.zones.hand):
            if c.name == UNHOLY and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                if target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.graveyard.append(target)
                gs._log(f"  Unholy Heat → kill {target.name}")
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

    def respond_to_spell(self, gs, opponent, spell):
        """Counter key spells. Murktide's primary interaction point."""
        if not opponent: return None
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        # Use removal on big threats
        if opp_creatures:
            target = max(opp_creatures, key=lambda c: safe_power(c))
            if safe_power(target) >= 3:
                for c in gs.zones.hand:
                    if c.name in REMOVAL and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        return c
        # Counter if we have mana
        for c in gs.zones.hand:
            if c.name in COUNTERS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                return c
        return None

    def declare_attackers(self, gs, opponent):
        from engine.keywords import KWTag
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land(): continue
            if getattr(c, 'summoning_sickness', False): continue
            if getattr(c, 'tapped', False): continue
            if c.has(Tag.CREATURE):
                attackers.append(c)
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        # Murktide can block with big flyers
        assignments = {}
        if not attackers: return assignments
        murktides = [c for c in gs.zones.battlefield
                     if c.name == MURKTIDE and not getattr(c, 'tapped', False)]
        if murktides:
            # Block the biggest attacker with Murktide (it's huge)
            biggest = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest) >= 3:
                assignments[id(biggest)] = [murktides[0]]
        return assignments

    def end_step_actions(self, gs, opponent):
        # Ragavan treasure on combat damage
        from engine.keywords import KWTag
        ragavans = sum(1 for c in gs.zones.battlefield
                       if c.name == RAGAVAN
                       and (not getattr(c, 'summoning_sickness', False)
                            or KWTag.HASTE in getattr(c, 'tags', set())))
        self._treasures += ragavans

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = c.name.lower()
            if 'tarn' in n or 'delta' in n or 'mire' in n: return 0
            if 'vents' in n: return 1
            return 3
        gs.play_land(min(lands, key=score))
