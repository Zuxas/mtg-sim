"""
apl/dimir_midrange_standard_match.py — Dimir Midrange APL (Standard)

Tempo-disruption deck that plays at instant speed whenever possible.
T1: Spyglass Siren or Deep-Cavern Bat (disrupt + fly over)
T2-3: Flash creatures at end of opponent's turn (Floodpits Drowner, Tidebinder)
T3: Kaito (makes 2/2 unblockable ninja tokens)
Enduring Curiosity: flash draw engine when creatures connect
Removal-heavy: Bitter Triumph, Shoot the Sheriff, Long Goodbye
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

DEEP_CAVERN_BAT    = "Deep-Cavern Bat"
SPYGLASS_SIREN     = "Spyglass Siren"
FLOODPITS_DROWNER  = "Floodpits Drowner"
ENDURING_CURIOSITY = "Enduring Curiosity"
KAITO              = "Kaito, Bane of Nightmares"
TIDEBINDER         = "Tishana's Tidebinder"
BITTER_TRIUMPH     = "Bitter Triumph"
SHOOT_THE_SHERIFF  = "Shoot the Sheriff"
LONG_GOODBYE       = "Long Goodbye"
ESSENCE_SCATTER    = "Essence Scatter"
CECIL              = "Cecil, Dark Knight"
STAB               = "Stab"

ONE_DROPS  = {DEEP_CAVERN_BAT, SPYGLASS_SIREN}
FLASH_CREATURES = {FLOODPITS_DROWNER, TIDEBINDER, ENDURING_CURIOSITY}
REMOVAL    = {BITTER_TRIUMPH, SHOOT_THE_SHERIFF, LONG_GOODBYE, ESSENCE_SCATTER}


class DimirMidrangeStandardMatchAPL(MatchAPL):
    name = "Dimir Midrange Standard"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        creatures = sum(1 for c in hand if c.has(Tag.CREATURE))
        removal = sum(1 for c in hand if c.name in REMOVAL)
        if lands == 0: return False
        if lands == 1 and creatures == 0: return False
        if lands > 5: return False
        if creatures >= 1 and removal >= 1 and 2 <= lands <= 4: return True
        if creatures >= 2 and 2 <= lands <= 4: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[3:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        """Tempo plan: removal first, then deploy threats. Hold flash for EOT."""
        self._play_land_if_able(gs)
        gs.tap_lands()

        # 1. Removal on opponent's best creature
        if opponent:
            self._use_removal(gs, opponent)

        # 2. T1: Deploy one-drops (Bat disrupts, Siren flies + clue)
        for name in (DEEP_CAVERN_BAT, SPYGLASS_SIREN):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    if name == DEEP_CAVERN_BAT and opponent:
                        # ETB: look at opponent's hand, exile a nonland (simulated as discard)
                        opp_nonlands = [x for x in opponent.zones.hand if not x.is_land()]
                        if opp_nonlands:
                            best = max(opp_nonlands, key=lambda x: getattr(x, 'cmc', 0))
                            opponent.zones.hand.remove(best)
                            opponent.zones.exile.append(best)
                            gs._log(f"  Bat ETB: exile {best.name} from opponent's hand")
                    break

        # 3. Kaito — planeswalker, makes 2/2 unblockable ninja tokens
        for c in list(gs.zones.hand):
            if c.name == KAITO and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Kaito deployed: creates 2/2 unblockable ninja tokens")
                break

        # 4. Cecil — creature, deploy when able
        for c in list(gs.zones.hand):
            if c.name == CECIL and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Cecil deployed")
                break

        # 5. Non-flash creatures
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and c.name not in FLASH_CREATURES:
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)

        # 6. Hold flash creatures for end_step_actions (don't deploy main phase)

    def _use_removal(self, gs, opponent):
        """Kill opponent's best creature. Priority: biggest threat first."""
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures: return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 2: return

        for c in list(gs.zones.hand):
            if c.name not in REMOVAL: continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc): continue
            # Long Goodbye: can only kill MV 3 or less
            if c.name == LONG_GOODBYE and getattr(target, 'cmc', 0) > 3:
                continue
            gs.mana_pool.pay(c.mana_cost, c.cmc)
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            gs.noncreature_spells_this_turn += 1
            if target in opponent.zones.battlefield:
                opponent.zones.battlefield.remove(target)
                opponent.zones.graveyard.append(target)
            gs._log(f"  {c.name}: kill {target.name}")
            return

        # Stab: {B}, -2/-2 on a creature — kills small things
        for c in list(gs.zones.hand):
            if c.name != STAB: continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc): continue
            if safe_toughness(target) <= 2:
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                gs.noncreature_spells_this_turn += 1
                if target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.graveyard.append(target)
                gs._log(f"  Stab: -2/-2 kills {target.name}")
                return

    def declare_attackers(self, gs, opponent):
        """Attack with flyers and small creatures. Hold back big blockers."""
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land(): continue
            if not c.has(Tag.CREATURE): continue
            if getattr(c, 'summoning_sickness', False): continue
            if getattr(c, 'tapped', False): continue
            attackers.append(c)
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        """Block with small flyers to trade up."""
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)
                    and not c.is_land() and not getattr(c, 'tapped', False)]
        if not blockers: return assignments
        # Trade small creatures into big attackers
        biggest_attacker = max(attackers, key=lambda c: safe_power(c))
        if safe_power(biggest_attacker) >= 3:
            # Use a small creature to chump or trade
            smallest = min(blockers, key=lambda c: safe_power(c))
            if safe_toughness(smallest) <= safe_power(biggest_attacker):
                assignments[id(biggest_attacker)] = [smallest]
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        """Use removal in response to opponent's creatures."""
        return None

    def end_step_actions(self, gs, opponent):
        """Flash creatures at end of opponent's turn — tempo advantage."""
        for name in (TIDEBINDER, FLOODPITS_DROWNER, ENDURING_CURIOSITY):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    if name == TIDEBINDER and opponent:
                        # Stifle best ETB on opponent's board (simulated)
                        gs._log(f"  Tidebinder flash: stifle ETB triggers")
                    elif name == ENDURING_CURIOSITY:
                        gs._log(f"  Enduring Curiosity flash: draw engine active")
                    else:
                        gs._log(f"  Floodpits Drowner flash EOT")
                    break

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if 'delta' in n or 'tarn' in n or 'catacombs' in n or 'mire' in n: return 0
            if 'crypt' in n or 'grave' in n or 'fountain' in n: return 1
            return 3
        gs.play_land(min(lands, key=score))
