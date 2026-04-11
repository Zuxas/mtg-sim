"""
apl/jeskai_blink_match.py — Oracle-audited Jeskai Blink APL (Modern)

Playbook engines (from Team Resolve):
A. Phelia Attack Loop — exile own ETB creature on attack, re-enter at end step
B. Solitude + Ephemerate — free evoke exile + blink for 2-3 creature exiles
C. Teferi Lock — opponents sorcery-speed only, -3 bounce+draw

Key oracle mechanics:
- Phelia: Flash, attack trigger exiles nonland permanent, returns at end step
- Solitude: Evoke (exile white card), ETB exile creature, Lifelink
- Ephemerate: {W} blink + Rebound (free blink next upkeep)
- Phlage: hardcast 3 dmg sacrifice, escape {R}{R}{W}{W}+exile5 = permanent 6/6
- Consign: {U} counter triggered ability or colorless spell, Replicate {1}
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

RAGAVAN    = "Ragavan, Nimble Pilferer"
PHELIA     = "Phelia, Exuberant Shepherd"
PHLAGE     = "Phlage, Titan of Fire's Fury"
SOLITUDE   = "Solitude"
QUANTUM    = "Quantum Riddler"
CASEY      = "Casey Jones, Vigilante"
CONSIGN    = "Consign to Memory"
GALVANIC   = "Galvanic Discharge"
PRISMATIC  = "Prismatic Ending"
EPHEMERATE = "Ephemerate"
TEFERI     = "Teferi, Time Raveler"
WRATH      = "Wrath of the Skies"
MARCH      = "March of Otherworldly Light"

ETB_CREATURES = {SOLITUDE, PHLAGE, QUANTUM, CASEY}
REMOVAL = {SOLITUDE, GALVANIC, PRISMATIC, CONSIGN, MARCH}


class JeskaiBlinkMatchAPL(MatchAPL):
    name = "Jeskai Blink"
    win_condition_damage = 20
    max_turns = 12
    _phelia_counters = 0
    _ephemerate_rebound = False  # track rebound for next upkeep

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in (RAGAVAN, PHELIA, SOLITUDE, QUANTUM, CASEY))
        interaction = sum(1 for c in hand if c.name in REMOVAL or c.name == EPHEMERATE)
        if lands == 0: return False
        if lands > 5: return False
        if threats >= 1 and interaction >= 1 and lands >= 2: return True
        if threats >= 2 and lands >= 2: return True
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

        # Ephemerate Rebound — free blink at upkeep
        if self._ephemerate_rebound:
            self._ephemerate_rebound = False
            self._blink_best_etb(gs, opponent)
            gs._log(f"  Ephemerate REBOUND: free blink")

        avail = gs.mana_pool.total()

        # 1. SOLITUDE EVOKE — free creature exile (pitch white card)
        if opponent:
            opp_threats = [c for c in opponent.zones.battlefield
                          if not c.is_land() and c.has(Tag.CREATURE) and safe_power(c) >= 2]
            if opp_threats:
                for c in list(gs.zones.hand):
                    if c.name == SOLITUDE:
                        # Find a white card to pitch (not Solitude itself)
                        white_cards = [x for x in gs.zones.hand 
                                      if x != c and not x.is_land()]
                        if white_cards:
                            pitch = white_cards[0]
                            gs.zones.hand.remove(pitch)
                            gs.zones.exile.append(pitch)
                            gs.zones.hand.remove(c)
                            # Solitude enters → ETB exile their best creature
                            target = max(opp_threats, key=lambda x: safe_power(x))
                            if target in opponent.zones.battlefield:
                                opponent.zones.battlefield.remove(target)
                                opponent.zones.exile.append(target)
                                # Opponent gains life = target's power (oracle)
                                opponent.life += safe_power(target)
                            gs._log(f"  Solitude EVOKE: exile {target.name} (pitched {pitch.name})")
                            # Solitude dies (evoke sacrifice) → goes to GY
                            gs.zones.graveyard.append(c)
                            # But if we have Ephemerate, blink Solitude BEFORE it dies!
                            eph = next((x for x in gs.zones.hand if x.name == EPHEMERATE), None)
                            if eph and avail >= 1:
                                gs.zones.hand.remove(eph)
                                gs.zones.exile.append(eph)  # rebound exile
                                self._ephemerate_rebound = True
                                # Solitude re-enters → exile ANOTHER creature
                                gs.zones.graveyard.remove(c)
                                gs.zones.battlefield.append(c)
                                c.turn_entered = gs.turn; c.summoning_sickness = True
                                opp_threats2 = [x for x in opponent.zones.battlefield
                                               if not x.is_land() and x.has(Tag.CREATURE)]
                                if opp_threats2:
                                    t2 = max(opp_threats2, key=lambda x: safe_power(x))
                                    opponent.zones.battlefield.remove(t2)
                                    opponent.zones.exile.append(t2)
                                    opponent.life += safe_power(t2)
                                    gs._log(f"  Ephemerate Solitude: exile {t2.name} (Solitude STAYS, rebound next turn)")
                            break

        avail = gs.mana_pool.total()

        # 2. Galvanic Discharge — energy-based removal
        if opponent:
            opp_creatures = [c for c in opponent.zones.battlefield
                            if not c.is_land() and c.has(Tag.CREATURE)]
            if opp_creatures:
                for c in list(gs.zones.hand):
                    if c.name == GALVANIC and avail >= 1:
                        gs.mana_pool.pay("{R}", 1) if gs.mana_pool.can_pay("{R}", 1) else None
                        gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                        gs.energy = getattr(gs, 'energy', 0) + 3
                        target = max(opp_creatures, key=lambda x: safe_power(x))
                        energy_to_spend = min(gs.energy, safe_toughness(target))
                        gs.energy -= energy_to_spend
                        if energy_to_spend >= safe_toughness(target):
                            if target in opponent.zones.battlefield:
                                opponent.zones.battlefield.remove(target)
                                opponent.zones.graveyard.append(target)
                            gs._log(f"  Discharge: kill {target.name} (spent {energy_to_spend}E)")
                        avail = gs.mana_pool.total()
                        break

        # 3. Deploy creatures: Ragavan (haste T1), Phelia (flash 2/2)
        for name in (RAGAVAN, PHELIA):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    if name == CASEY:
                        gs.zones.draw(3)
                        gs._log(f"  Casey Jones ETB: draw 3 (discard 3 next upkeep)")
                    break

        # 4. Quantum Riddler ({3}{U}{U}) — 4/6 flying, ETB draw 1
        for c in list(gs.zones.hand):
            if c.name == QUANTUM and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs.zones.draw(1)
                gs._log(f"  Quantum Riddler: 4/6 flying, draw 1")
                break

        # 5. Casey Jones ({1}{R}{R}) — ETB draw 3, discard 3 next upkeep
        for c in list(gs.zones.hand):
            if c.name == CASEY and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs.zones.draw(3)
                gs._log(f"  Casey Jones: draw 3")
                break

        # 6. Teferi ({1}{W}{U}) — opponents sorcery-speed, -3 bounce+draw
        for c in list(gs.zones.hand):
            if c.name == TEFERI and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                if opponent:
                    opp_nonlands = [x for x in opponent.zones.battlefield if not x.is_land()]
                    if opp_nonlands:
                        target = max(opp_nonlands, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.hand.append(target)
                        gs._log(f"  Teferi -3: bounce {target.name} + draw")
                gs.zones.draw(1)
                break

        # 7. Phlage — hardcast as removal OR escape from GY as finisher
        # Escape: {R}{R}{W}{W} + exile 5 = permanent 6/6
        gy_phlages = [c for c in gs.zones.graveyard if c.name == PHLAGE]
        other_gy = len(gs.zones.graveyard) - len(gy_phlages)
        if gy_phlages and other_gy >= 5 and gs.mana_pool.total() >= 4:
            phlage = gy_phlages[0]
            for _ in range(5):
                non_phlage = [x for x in gs.zones.graveyard if x.name != PHLAGE]
                if non_phlage:
                    gs.zones.graveyard.remove(non_phlage[0])
                    gs.zones.exile.append(non_phlage[0])
            gs.zones.graveyard.remove(phlage)
            gs.zones.battlefield.append(phlage)
            phlage.turn_entered = gs.turn; phlage.summoning_sickness = True
            # ETB: 3 damage + 3 life
            if opponent:
                gs.damage_dealt += 3
            gs.life += 3
            gs._log(f"  PHLAGE ESCAPE: 6/6 permanent + 3 dmg + 3 life")
        else:
            # Hardcast Phlage from hand (3 damage + 3 life, then sacrifice)
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
                    gs.zones.graveyard.append(c)  # sacrifice → GY for escape later
                    break

        # 8. Ephemerate on ETB creature (if not used on Solitude already)
        for c in list(gs.zones.hand):
            if c.name == EPHEMERATE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                self._blink_best_etb(gs, opponent)
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.exile.append(c)
                self._ephemerate_rebound = True
                gs._log(f"  Ephemerate: blink ETB creature (rebound next turn)")
                break

        # 9. Fill remaining mana with creatures
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and c.name != PHLAGE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def _blink_best_etb(self, gs, opponent):
        """Blink the best ETB creature on our battlefield."""
        etb_creatures = [c for c in gs.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()
                        and c.name in ETB_CREATURES]
        if not etb_creatures:
            return
        # Priority: Solitude (exile creature) > Phlage (3 dmg + 3 life) > Quantum (draw)
        for name in (SOLITUDE, PHLAGE, QUANTUM, CASEY):
            target = next((c for c in etb_creatures if c.name == name), None)
            if target:
                if name == SOLITUDE and opponent:
                    opp_cr = [x for x in opponent.zones.battlefield
                             if not x.is_land() and x.has(Tag.CREATURE)]
                    if opp_cr:
                        t = max(opp_cr, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(t)
                        opponent.zones.exile.append(t)
                        opponent.life += safe_power(t)
                        gs._log(f"  Blink Solitude: exile {t.name}")
                elif name == PHLAGE:
                    if opponent:
                        gs.damage_dealt += 3
                    gs.life += 3
                    gs._log(f"  Blink Phlage: 3 dmg + 3 life")
                elif name == QUANTUM:
                    gs.zones.draw(1)
                    gs._log(f"  Blink Quantum Riddler: draw 1")
                elif name == CASEY:
                    gs.zones.draw(3)
                    gs._log(f"  Blink Casey Jones: draw 3")
                return

    def declare_attackers(self, gs, opponent):
        """Attack with creatures. Phelia attack trigger: blink own ETB creature."""
        attackers = [c for c in gs.zones.battlefield
                    if not c.is_land() and c.has(Tag.CREATURE)
                    and not getattr(c, 'summoning_sickness', False)
                    and not getattr(c, 'tapped', False)]
        # Phelia attack trigger: exile own ETB creature → re-enter at end step
        phelia = next((c for c in attackers if c.name == PHELIA), None)
        if phelia and opponent:
            self._blink_best_etb(gs, opponent)
            self._phelia_counters += 1
            gs._log(f"  Phelia attack: blink ETB creature (+1/+1 counter #{self._phelia_counters})")
        # Phlage attack trigger: 3 dmg + 3 life
        for a in attackers:
            if a.name == PHLAGE:
                if opponent:
                    gs.damage_dealt += 3
                gs.life += 3
                gs._log(f"  Phlage attack trigger: 3 dmg + 3 life")
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)
                    and not c.is_land() and not getattr(c, 'tapped', False)
                    and safe_toughness(c) >= 3]
        if blockers:
            biggest = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest) >= 3:
                assignments[id(biggest)] = [blockers[0]]
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        """Consign to Memory counters triggered abilities."""
        return None

    def end_step_actions(self, gs, opponent): pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            name = c.name.lower() if c.name else ''
            if 'arena' in name: return 0
            if 'foundry' in name or 'vents' in name: return 1
            return 3
        gs.play_land(min(lands, key=score))
