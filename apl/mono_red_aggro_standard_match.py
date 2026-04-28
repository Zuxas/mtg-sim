"""
apl/mono_red_aggro_standard_match.py — Mono Red Aggro (Standard)

Current-meta Mono Red from botboy 2026-04-03 top-8. Post-ban shell
— no Heartfire Hero, no Monstrous Rage.

Plan:
  T1  Hired Claw (2/1 haste for {R}) or Fanatical Firebrand (1/1 haste)
  T2  Hearthborn Battler (2/2 haste) or Razorkin Needlehead (pings ETB)
      or Scalding Viper (2/2 with cost-bump static to opp)
  T3  Kellan, Planar Trailblazer (curve-out legend) or Ojer Axonil,
      Deepest Might (deal damage always ≥ 4 — turns Shock into 4-dmg
      nuke and Burst Lightning into 4-dmg)
  T4  Nova Hellkite (4/4 flying haste dragon) or Tokka & Rahzar
      (5/5 Turtle legend)
  Burn: Burst Lightning (2, kicked 4), Shock (2 to creature/player),
  Scorching Shot (3 to creature), Sear (3 to creature, SB).

Ojer Axonil's static "If a source you control would deal damage to
a permanent or player, if that amount is less than 4, it deals 4
damage instead" retroactively boosts all burn when he's on board.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness


# Creatures
HIRED_CLAW          = "Hired Claw"
FANATICAL_FIREBRAND = "Fanatical Firebrand"
HEARTHBORN_BATTLER  = "Hearthborn Battler"
RAZORKIN            = "Razorkin Needlehead"
SCALDING_VIPER      = "Scalding Viper"
KELLAN              = "Kellan, Planar Trailblazer"
OJER_AXONIL         = "Ojer Axonil, Deepest Might"
NOVA_HELLKITE       = "Nova Hellkite"
TOKKA_RAHZAR        = "Tokka & Rahzar, Terrible Twos"

# Burn
BURST_LIGHTNING     = "Burst Lightning"
SHOCK               = "Shock"
SCORCHING_SHOT      = "Scorching Shot"
SEAR                = "Sear"


ONE_DROPS = {HIRED_CLAW, FANATICAL_FIREBRAND}
BURN_SPELLS = {BURST_LIGHTNING, SHOCK, SCORCHING_SHOT, SEAR}
REMOVAL_SPELLS = {BURST_LIGHTNING, SHOCK, SCORCHING_SHOT, SEAR}


class MonoRedAggroStandardMatchAPL(MatchAPL):
    ARCHETYPE = "aggro"
    name = "Mono Red Aggro (Standard)"
    win_condition_damage = 20
    max_turns = 8

    SB_PLANS = {
        "control": (
            ["4 Magebane Lizard", "2 Leyline of the Void",
             "3 Twisted Fealty"],
            ["3 Scorching Shot", "4 Scalding Viper",
             "1 Fanatical Firebrand", "1 Tokka & Rahzar, Terrible Twos"],
        ),
        "aggro": (
            ["3 Sear", "1 Scorching Shot",
             "2 Tokka & Rahzar, Terrible Twos"],
            ["3 Nova Hellkite", "1 Tokka & Rahzar, Terrible Twos",
             "2 Kellan, Planar Trailblazer"],
        ),
        "combo": (
            ["2 Leyline of the Void", "3 Sear",
             "2 Tokka & Rahzar, Terrible Twos"],
            ["3 Ojer Axonil, Deepest Might", "4 Scalding Viper"],
        ),
        "ramp": (
            ["4 Magebane Lizard", "2 Tokka & Rahzar, Terrible Twos",
             "3 Sear"],
            ["4 Scalding Viper", "1 Multiversal Passage",
             "4 Razorkin Needlehead"],
        ),
        "tempo": (
            ["3 Sear", "1 Scorching Shot", "3 Twisted Fealty"],
            ["3 Nova Hellkite", "4 Scalding Viper"],
        ),
    }

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        creatures = sum(1 for c in hand if c.has(Tag.CREATURE))
        burns = sum(1 for c in hand if c.name in BURN_SPELLS)
        if lands == 0 or lands > 4:
            return False
        if 2 <= lands <= 3 and creatures >= 1:
            return True
        if lands >= 2 and burns >= 2:
            return True
        if lands == 1 and creatures >= 2:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                         key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[3:] + spells)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """Mono Red aggro: deploy hasty creatures, burn blockers, face."""
        self._play_land_if_able(gs)
        gs.tap_lands()

        # Is Ojer Axonil on board? If so, burn damage floors at 4.
        ojer_active = any(c.name == OJER_AXONIL
                           for c in gs.zones.battlefield)

        # 1. Removal on opp's biggest creature (Ojer-boosted if active)
        if opponent:
            self._try_removal(gs, opponent, ojer_active)

        # 2. 1-drops
        for name in (HIRED_CLAW, FANATICAL_FIREBRAND):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # 3. 2-drops — Hearthborn Battler first (haste body)
        for name in (HEARTHBORN_BATTLER, SCALDING_VIPER, RAZORKIN):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    if name == RAZORKIN:
                        # ETB ping
                        dmg = max(1, 4 if ojer_active else 1)
                        gs.damage_dealt += dmg
                        gs._log(f"  Razorkin ETB: {dmg} ping "
                                f"({gs.damage_dealt})")
                    break

        # 4. 3-drops — Kellan then Ojer Axonil
        for name in (KELLAN, OJER_AXONIL):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    if c.name == OJER_AXONIL:
                        ojer_active = True  # now active for this turn
                    break

        # 5. 4+ drops — Tokka & Rahzar, Nova Hellkite
        for name in (TOKKA_RAHZAR, NOVA_HELLKITE):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # 6. Burn remaining mana to face (Ojer bumps to 4)
        for c in list(gs.zones.hand):
            if c.name not in BURN_SPELLS:
                continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                continue
            if c.name == SCORCHING_SHOT or c.name == SEAR:
                dmg_base = 3
            else:
                dmg_base = 2  # Burst / Shock unkicked
            dmg = max(dmg_base, 4 if ojer_active else dmg_base)
            gs.mana_pool.pay(c.mana_cost, c.cmc)
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            gs.damage_dealt += dmg
            gs.noncreature_spells_this_turn += 1
            tag = " (Ojer)" if ojer_active and dmg > dmg_base else ""
            gs._log(f"  {c.name} face: {dmg}{tag} ({gs.damage_dealt})")

        # 7. Any remaining creature
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def _try_removal(self, gs, opponent, ojer_active):
        opp_creatures = [c for c in opponent.zones.battlefield
                          if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures:
            return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 2:
            return
        for c in list(gs.zones.hand):
            if c.name not in REMOVAL_SPELLS:
                continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                continue
            if c.name in (SCORCHING_SHOT, SEAR):
                dmg_base = 3
            else:
                dmg_base = 2
            dmg = max(dmg_base, 4 if ojer_active else dmg_base)
            if dmg < safe_toughness(target):
                continue
            gs.mana_pool.pay(c.mana_cost, c.cmc)
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            gs.noncreature_spells_this_turn += 1
            if target in opponent.zones.battlefield:
                opponent.zones.battlefield.remove(target)
                opponent.zones.graveyard.append(target)
            gs._log(f"  {c.name} -> kill {target.name}")
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

    def declare_blockers(self, gs, opp, attackers):
        return {}  # aggro races

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        # Prefer untapped red-producing lands
        def score(c):
            n = (c.name or '').lower()
            if 'mountain' in n:
                return 0
            if 'steam vents' in n or 'riverpyre' in n or 'spirebluff' in n:
                return 1
            if 'rockface' in n or 'multiversal' in n:
                return 2
            return 3
        gs.play_land(min(lands, key=score))
