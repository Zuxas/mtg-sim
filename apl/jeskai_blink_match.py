"""
apl/jeskai_blink_match.py — Match-aware Jeskai Blink APL (Modern)

The most interactive deck in Modern. Key match mechanics:
1. Solitude: FREE removal (pitch a white card to exile target creature)
2. Consign to Memory: hard counter (2 mana)
3. Galvanic Discharge: energy-based removal
4. Prismatic Ending: exile low-CMC permanents
5. Ephemerate: blink Solitude/Phlage for double ETB triggers
6. Teferi: bounce permanent + draw, locks opponents to sorcery speed
7. Wrath of the Skies: board wipe when behind
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

REMOVAL = {SOLITUDE, GALVANIC, PRISMATIC, CONSIGN}
CREATURES = {RAGAVAN, PHELIA, PHLAGE, QUANTUM, CASEY, SOLITUDE}


class JeskaiBlinkMatchAPL(MatchAPL):
    name = "Jeskai Blink"
    win_condition_damage = 20
    max_turns = 12
    _treasures = 0

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in CREATURES)
        interaction = sum(1 for c in hand if c.name in REMOVAL)
        if lands == 0: return False
        if lands > 5: return False
        if threats >= 1 and interaction >= 1 and lands >= 2: return True
        if threats >= 2 and lands >= 2: return True
        if any(c.name == RAGAVAN for c in hand) and lands >= 1: return True
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
        """Highly interactive: removal first, then deploy threats."""
        if self._treasures > 0:
            use = min(self._treasures, 2)
            gs.mana_pool.flex += use
            self._treasures -= use

        self._play_land_if_able(gs)

        # 1. Solitude pitch — FREE removal (exile a white card to exile creature)
        if opponent:
            self._try_solitude_pitch(gs, opponent)

        # 2. Galvanic Discharge / Prismatic Ending on remaining threats
        if opponent:
            self._use_paid_removal(gs, opponent)

        # 3. Deploy threats: Ragavan (haste), Phelia, Quantum Riddler
        from engine.keywords import KWTag
        for name in (RAGAVAN, PHELIA, QUANTUM, CASEY):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    # Guide-like triggers for Phelia
                    break

        # 4. Teferi — bounce their best permanent + draw
        for c in list(gs.zones.hand):
            if c.name == TEFERI and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                if opponent:
                    opp_nonlands = [x for x in opponent.zones.battlefield if not x.is_land()]
                    if opp_nonlands:
                        target = max(opp_nonlands, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.hand.append(target)
                        gs._log(f"  Teferi → bounce {target.name}")
                gs.zones.draw(1)
                break

        # 5. Phlage hardcast (3 damage + 3 life, sacrifice, to GY for escape)
        for c in list(gs.zones.hand):
            if c.name == PHLAGE and gs.mana_pool.total() >= 3:
                if gs.mana_pool.can_pay("{1}{R}{W}", 3):
                    gs.mana_pool.pay("{1}{R}{W}", 3)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    if opponent:
                        # Target opponent's best creature or face
                        opp_creatures = [x for x in opponent.zones.battlefield
                                         if not x.is_land() and x.has(Tag.CREATURE)
                                         and safe_toughness(x) <= 3]
                        if opp_creatures:
                            target = max(opp_creatures, key=lambda x: safe_power(x))
                            opponent.zones.battlefield.remove(target)
                            opponent.zones.graveyard.append(target)
                            gs._log(f"  Phlage → kill {target.name} + 3 life")
                        else:
                            gs.damage_dealt += 3
                            gs._log(f"  Phlage → 3 face ({gs.damage_dealt}) + 3 life")
                    else:
                        gs.damage_dealt += 3
                    gs.life += 3
                    break

        # 6. Ephemerate — blink Solitude for double exile
        for c in list(gs.zones.hand):
            if c.name == EPHEMERATE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                solitudes = [x for x in gs.zones.battlefield if x.name == SOLITUDE]
                if solitudes and opponent:
                    opp_creatures = [x for x in opponent.zones.battlefield
                                     if not x.is_land() and x.has(Tag.CREATURE)]
                    if opp_creatures:
                        gs.cast_spell(c)
                        target = max(opp_creatures, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.exile.append(target)
                        gs._log(f"  Ephemerate Solitude → exile {target.name}")
                break

        # 7. Fill curve
        changed = True
        attempts = 0
        while changed and attempts < 15:
            changed = False
            attempts += 1
            castable = [c for c in gs.zones.hand
                        if c.has(Tag.CREATURE) and c.name not in REMOVAL
                        and gs.mana_pool.can_cast(c.mana_cost, c.cmc)]
            if castable:
                spell = min(castable, key=lambda c: getattr(c, 'cmc', 0))
                if gs.cast_spell(spell):
                    changed = True
                else:
                    break

    def _try_solitude_pitch(self, gs: GameState, opponent: GameState):
        """Solitude: exile a white card from hand to exile target creature. FREE."""
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures: return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 3: return  # save Solitude for big threats

        solitude = next((c for c in gs.zones.hand if c.name == SOLITUDE), None)
        if not solitude: return

        # Need a white card to pitch (not the Solitude itself)
        white_cards = [c for c in gs.zones.hand
                       if c != solitude and 'W' in (getattr(c, 'mana_cost', '') or '')]
        if not white_cards: return

        # Pitch the worst white card
        pitch = min(white_cards, key=lambda c: safe_power(c) if c.has(Tag.CREATURE) else 0)
        gs.zones.hand.remove(solitude)
        gs.zones.hand.remove(pitch)
        gs.zones.exile.append(pitch)
        # Solitude enters as a 3/2 lifelink creature
        gs.zones.battlefield.append(solitude)
        solitude.turn_entered = gs.turn
        solitude.summoning_sickness = True
        # Exile target creature
        if target in opponent.zones.battlefield:
            opponent.zones.battlefield.remove(target)
            opponent.zones.exile.append(target)
        # Opponent gains life equal to target's power (Solitude's drawback)
        opponent.life += safe_power(target)
        gs._log(f"  Solitude (pitch {pitch.name}) → exile {target.name}")

    def _use_paid_removal(self, gs: GameState, opponent: GameState):
        """Galvanic Discharge / Prismatic Ending on creatures."""
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures: return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 2: return

        # Galvanic Discharge
        energy = getattr(gs, 'energy', 0)
        for c in list(gs.zones.hand):
            if c.name == GALVANIC and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                gs.energy = getattr(gs, 'energy', 0) + 3
                spent = min(gs.energy, safe_toughness(target))
                gs.energy -= spent
                if spent >= safe_toughness(target) and target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.graveyard.append(target)
                    gs._log(f"  Galvanic → kill {target.name} (spent {spent}E)")
                return

        # Prismatic Ending
        target_cmc = getattr(target, 'cmc', 0)
        if target_cmc <= 3:
            for c in list(gs.zones.hand):
                if c.name == PRISMATIC and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    if target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.exile.append(target)
                    gs._log(f"  Prismatic Ending → exile {target.name}")
                    return

    def respond_to_spell(self, gs, opponent, spell):
        """Consign to Memory — hard counter for 2 mana."""
        for c in gs.zones.hand:
            if c.name == CONSIGN and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                return c
        # Fall back to removal
        if opponent:
            opp_creatures = [c for c in opponent.zones.battlefield
                             if not c.is_land() and safe_power(c) >= 3]
            if opp_creatures:
                for c in gs.zones.hand:
                    if c.name == GALVANIC and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
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
        """Block with Solitude (3/2 lifelink) to gain life."""
        assignments = {}
        if not attackers: return assignments
        solitudes = [c for c in gs.zones.battlefield
                     if c.name == SOLITUDE and not getattr(c, 'tapped', False)]
        if solitudes and attackers:
            biggest = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest) >= 2:
                assignments[id(biggest)] = [solitudes[0]]
        return assignments

    def end_step_actions(self, gs, opponent):
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
            if 'mesa' in n or 'strand' in n or 'tarn' in n: return 0
            if 'foundry' in n or 'fountain' in n: return 1
            if 'arena' in n: return 2
            return 4
        gs.play_land(min(lands, key=score))
