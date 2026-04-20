"""
apl/esper_raffine_standard_match.py — Esper Raffine APL (Standard)

Control-midrange deck that clears the board, then deploys must-answer threats.
T1-2: Removal (Cut Down, Go for the Throat)
T2: Faerie Mastermind (flash, draw trigger punishes opponent)
T3: Liliana of the Veil (+1 discard, -2 sacrifice creature)
T4: Sheoldred (must-kill, drains opponent every draw)
Late: Horned Loch-Whale (6/6 flash), Doomsday Excruciator
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

SHEOLDRED           = "Sheoldred, the Apocalypse"
LILIANA             = "Liliana of the Veil"
FAERIE_MASTERMIND   = "Faerie Mastermind"
HORNED_LOCH_WHALE   = "Horned Loch-Whale"
JACE                = "Jace, the Perfected Mind"
CUT_DOWN            = "Cut Down"
GO_FOR_THE_THROAT   = "Go for the Throat"
ANOINT              = "Anoint with Affliction"
UNHOLY_ANNEX        = "Unholy Annex // Ritual Chamber"
SHOOT_THE_SHERIFF   = "Shoot the Sheriff"
BINDING_NEGOTIATION = "Binding Negotiation"
DEADLY_COVER_UP     = "Deadly Cover-Up"

REMOVAL = {CUT_DOWN, GO_FOR_THE_THROAT, ANOINT, SHOOT_THE_SHERIFF}
FLASH_CREATURES = {FAERIE_MASTERMIND, HORNED_LOCH_WHALE}


class EsperRaffineStandardMatchAPL(MatchAPL):
    name = "Esper Raffine Standard"
    win_condition_damage = 20
    max_turns = 15

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        removal = sum(1 for c in hand if c.name in REMOVAL)
        threats = sum(1 for c in hand if c.has(Tag.CREATURE) or
                      c.name in (SHEOLDRED, LILIANA, JACE))
        if lands < 2: return False
        if lands > 5: return False
        if removal >= 1 and threats >= 1 and 3 <= lands <= 4: return True
        if removal >= 2 and lands >= 3: return True
        if threats >= 1 and lands >= 3: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[4:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        """Control plan: removal first, then deploy threats behind clear board."""
        self._play_land_if_able(gs)
        gs.tap_lands()

        # 1. Removal FIRST — clear board before deploying
        if opponent:
            self._use_removal(gs, opponent)

        # 2. Deadly Cover-Up — board wipe {3}{B}{B}, destroys all creatures
        if opponent:
            opp_creatures = [c for c in opponent.zones.battlefield
                             if not c.is_land() and c.has(Tag.CREATURE)]
            if len(opp_creatures) >= 3:
                for c in list(gs.zones.hand):
                    if c.name == DEADLY_COVER_UP and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        gs.mana_pool.pay(c.mana_cost, c.cmc)
                        gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                        gs.noncreature_spells_this_turn += 1
                        total_killed = 0
                        for cr in list(opponent.zones.battlefield):
                            if cr.has(Tag.CREATURE) and not cr.is_land():
                                opponent.zones.battlefield.remove(cr)
                                opponent.zones.graveyard.append(cr)
                                total_killed += 1
                        for cr in list(gs.zones.battlefield):
                            if cr.has(Tag.CREATURE) and not cr.is_land():
                                gs.zones.battlefield.remove(cr)
                                gs.zones.graveyard.append(cr)
                                total_killed += 1
                        gs._log(f"  Deadly Cover-Up: destroy {total_killed} creatures")
                        break

        # 3. Binding Negotiation — {2}{B}, opponent sacrifices nonland nontoken permanent
        if opponent:
            opp_nonlands = [c for c in opponent.zones.battlefield
                            if not c.is_land()]
            if opp_nonlands and gs.mana_pool.total() >= 3:
                for c in list(gs.zones.hand):
                    if c.name == BINDING_NEGOTIATION and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        gs.mana_pool.pay(c.mana_cost, c.cmc)
                        gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                        gs.noncreature_spells_this_turn += 1
                        # Opponent sacrifices worst nonland nontoken permanent
                        target = min(opp_nonlands, key=lambda x: safe_power(x)
                                     if x.has(Tag.CREATURE) else 0)
                        if target in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(target)
                            opponent.zones.graveyard.append(target)
                        gs._log(f"  Binding Negotiation: opponent sacrifices {target.name}")
                        break

        # 4. Liliana of the Veil — T3 planeswalker
        for c in list(gs.zones.hand):
            if c.name == LILIANA and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                if opponent:
                    opp_cr = [x for x in opponent.zones.battlefield
                              if not x.is_land() and x.has(Tag.CREATURE)]
                    if opp_cr:
                        # -2: sacrifice a creature
                        target = min(opp_cr, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.graveyard.append(target)
                        gs._log(f"  Liliana -2: opponent sacrifices {target.name}")
                    else:
                        # +1: each player discards
                        gs._log(f"  Liliana +1: each player discards")
                break

        # 3. Sheoldred — T4 must-kill, drains on every draw
        for c in list(gs.zones.hand):
            if c.name == SHEOLDRED and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Sheoldred: 4/5 deathtouch, opponent loses 2 per draw")
                break

        # 4. Jace — planeswalker, mill win condition
        for c in list(gs.zones.hand):
            if c.name == JACE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Jace deployed: mill engine")
                break

        # 5. Unholy Annex — token generator
        for c in list(gs.zones.hand):
            if c.name == UNHOLY_ANNEX and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 6. Remaining non-flash creatures
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and c.name not in FLASH_CREATURES:
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)

        # Sheoldred drain: opponent loses 2 life per draw step (simulated)
        if any(c.name == SHEOLDRED for c in gs.zones.battlefield):
            if opponent:
                gs.damage_dealt += 2  # drain per turn cycle
                gs.life += 2
                gs._log(f"  Sheoldred drain: opponent -2, you +2")

    def _use_removal(self, gs, opponent):
        """Kill opponent's best creature. Use cheap removal first."""
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures: return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 1: return

        # Cut Down first (cheap, 1 mana) — kills power/toughness total <= 5
        for c in list(gs.zones.hand):
            if c.name == CUT_DOWN and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                total = safe_power(target) + safe_toughness(target)
                if total <= 5:
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                    gs.noncreature_spells_this_turn += 1
                    if target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.graveyard.append(target)
                    gs._log(f"  Cut Down: kill {target.name}")
                    return

        # Go for the Throat (2 mana, kills non-artifact)
        for c in list(gs.zones.hand):
            if c.name == GO_FOR_THE_THROAT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                gs.noncreature_spells_this_turn += 1
                if target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.graveyard.append(target)
                gs._log(f"  Go for the Throat: kill {target.name}")
                return

        # Shoot the Sheriff (2 mana {1}{B}, destroys non-outlaw creature)
        for c in list(gs.zones.hand):
            if c.name == SHOOT_THE_SHERIFF and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                gs.noncreature_spells_this_turn += 1
                if target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.graveyard.append(target)
                gs._log(f"  Shoot the Sheriff: kill {target.name}")
                return

        # Anoint with Affliction (exile removal)
        for c in list(gs.zones.hand):
            if c.name == ANOINT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                gs.noncreature_spells_this_turn += 1
                if target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.exile.append(target)
                gs._log(f"  Anoint: exile {target.name}")
                return

    def declare_attackers(self, gs, opponent):
        """Attack with everything — Sheoldred is a 4/5 beater too."""
        return [c for c in gs.zones.battlefield
                if not c.is_land() and c.has(Tag.CREATURE)
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        """Always block if favorable trade."""
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)
                    and not c.is_land() and not getattr(c, 'tapped', False)]
        if not blockers: return assignments
        for attacker in sorted(attackers, key=lambda c: safe_power(c), reverse=True):
            for b in blockers:
                if b in [v for vs in assignments.values() for v in vs]:
                    continue  # already assigned
                # Block if we survive or trade favorably
                if safe_toughness(b) > safe_power(attacker):
                    assignments[id(attacker)] = [b]
                    break
                elif safe_power(b) >= safe_toughness(attacker) and safe_power(attacker) >= 3:
                    assignments[id(attacker)] = [b]
                    break
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        """Flash creatures at end of opponent's turn."""
        for name in (FAERIE_MASTERMIND, HORNED_LOCH_WHALE):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    if name == FAERIE_MASTERMIND:
                        gs._log(f"  Faerie Mastermind flash: draw trigger active")
                    else:
                        gs._log(f"  Horned Loch-Whale flash: 6/6 EOT")
                    break

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if 'delta' in n or 'strand' in n or 'flats' in n or 'catacombs' in n: return 0
            if 'crypt' in n or 'fountain' in n or 'grave' in n or 'shrine' in n: return 1
            return 3
        gs.play_land(min(lands, key=score))
